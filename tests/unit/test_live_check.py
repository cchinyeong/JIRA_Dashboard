import copy
import json
from pathlib import Path

import httpx
import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.live_check import main
from jira_dashboard.integrations.live_report import analyse_ticket, format_report
from jira_dashboard.services.secrets import JIRA_PAT, InMemorySecretStore
from jira_dashboard.utils.redaction import clear_secrets

FIXTURES = Path(__file__).parent / "fixtures"
TOKEN = "tok-live-secret-123456"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def epic_payload() -> dict:
    payload = load("issue_cae_1558.json")
    payload["key"] = "CAE-1513"
    payload["fields"]["issuetype"] = {"name": "Epic"}
    payload["fields"]["components"] = [{"name": "Verification"}]
    return payload


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    clear_secrets()
    yield
    clear_secrets()


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://jira.example.com")
    return get_settings()


@pytest.fixture
def store() -> InMemorySecretStore:
    secrets = InMemorySecretStore()
    secrets.set(JIRA_PAT, TOKEN)
    return secrets


def make_transport(issues: dict[str, dict], methods: list[str], field_status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        path = request.url.path
        if path == "/rest/api/2/field":
            if field_status != 200:
                return httpx.Response(field_status)
            return httpx.Response(200, json=[{"id": "customfield_10001", "name": "Epic Link"}])
        key = path.rsplit("/", 1)[-1]
        if key in issues:
            return httpx.Response(200, json=issues[key])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def run(configured, store, transport, tmp_path, keys):
    return main(
        [*keys, "--output", str(tmp_path / "out")],
        settings=configured,
        secret_store=store,
        transport=transport,
    )


def test_report_task_with_parent(configured) -> None:
    report = analyse_ticket(load("task_epic_link.json"), configured, "Task")
    assert report.mapped and report.details["parent"] == "CAE-1513"
    assert report.epic_shape == "str"
    assert report.sprint_format == "legacy"
    assert not report.type_mismatch


def test_report_unmapped_and_mismatch(configured) -> None:
    bad = load("issue_cae_1558.json")
    del bad["fields"]["project"]
    good = analyse_ticket(load("task_risk_link.json"), configured, "Risk")
    broken = analyse_ticket(bad, configured, "Risk")
    assert not broken.mapped and "project" in broken.error
    assert good.type_mismatch
    text = format_report([broken, good], [], {"CAE-9": "Not found (404)."}, [])
    assert "NOT MAPPED" in text
    assert "expected type Risk, got Task" in text
    assert "CAE-9: NOT RETRIEVED" in text
    assert "is child of" in text


def test_success_writes_sanitised_fixtures(configured, store, tmp_path, capsys) -> None:
    methods: list[str] = []
    issues = {
        "CAE-1513": epic_payload(),
        "CAE-1558": load("issue_cae_1558.json"),
        "CAE-1628": load("task_epic_link.json"),
    }
    code = run(configured, store, make_transport(issues, methods), tmp_path, list(issues))
    out = capsys.readouterr().out
    assert code == 0
    assert set(methods) == {"GET"}
    assert "parent: CAE-1513" in out
    assert "customfield_10001: customfield_10001 -> ok" not in out
    assert "epic_link: customfield_10001 -> ok" in out
    assert TOKEN not in out
    files = sorted((tmp_path / "out").glob("*.json"))
    assert [f.name for f in files] == ["CAE-1513.json", "CAE-1558.json", "CAE-1628.json"]
    for file in files:
        content = file.read_text(encoding="utf-8")
        assert TOKEN not in content and "CY Chong" not in content and "Mohamad" not in content


def test_partial_failure_keeps_other_tickets(configured, store, tmp_path, capsys) -> None:
    issues = {"CAE-1558": load("issue_cae_1558.json")}
    code = run(configured, store, make_transport(issues, []), tmp_path, ["CAE-1592", "CAE-1558"])
    out = capsys.readouterr().out
    assert code == 1
    assert "CAE-1592: NOT RETRIEVED" in out
    assert (tmp_path / "out" / "CAE-1558.json").exists()
    assert not (tmp_path / "out" / "CAE-1592.json").exists()


def test_authentication_failure_stops_early(configured, store, tmp_path, capsys) -> None:
    methods: list[str] = []
    transport = make_transport({}, methods, field_status=401)
    code = run(configured, store, transport, tmp_path, ["CAE-1558"])
    out = capsys.readouterr().out
    assert code == 1
    assert "rejected the token" in out
    assert TOKEN not in out
    assert methods == ["GET"]


def test_placeholder_url_stops_before_requests(store, tmp_path, capsys) -> None:
    methods: list[str] = []
    code = main(
        ["--output", str(tmp_path / "out")],
        settings=get_settings(),
        secret_store=store,
        transport=make_transport({}, methods),
    )
    assert code == 1
    assert "jira.base_url" in capsys.readouterr().out
    assert methods == []


def test_missing_token(configured, tmp_path, capsys) -> None:
    methods: list[str] = []
    code = run(configured, InMemorySecretStore(), make_transport({}, methods), tmp_path, [])
    assert code == 1
    assert "docs/security.md" in capsys.readouterr().out
    assert methods == []


def test_leak_blocks_writing(configured, store, tmp_path, capsys) -> None:
    leaky = copy.deepcopy(load("task_epic_link.json"))
    sprint = leaky["fields"]["customfield_10000"][1]
    leaky["fields"]["customfield_10000"][1] = sprint.replace("Static Sprint", "bob@corp.com")
    code = run(configured, store, make_transport({"CAE-1628": leaky}, []), tmp_path, ["CAE-1628"])
    out = capsys.readouterr().out
    assert code == 1
    assert "e-mail address" in out
    assert "bob@corp.com" not in out
    assert not (tmp_path / "out").exists()
