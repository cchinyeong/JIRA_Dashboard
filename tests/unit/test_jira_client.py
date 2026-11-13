import copy
import json
import re
from pathlib import Path

import httpx
import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations import (
    JiraApiError,
    JiraClient,
    JiraNotConfiguredError,
    JiraOnPremClient,
    TicketBatch,
    jira_onprem,
    map_issue,
)
from jira_dashboard.models import FindingCode, Project, Ticket, TicketKind, TicketStatus
from jira_dashboard.services.secrets import (
    JIRA_PAT,
    InMemorySecretStore,
    MissingSecretError,
)
from jira_dashboard.utils.redaction import clear_secrets

FIXTURES = Path(__file__).parent / "fixtures"
TOKEN = "tok-client-secret-123456"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def issue(key: str, base: str = "issue_cae_1558.json", **fields) -> dict:
    payload = load(base)
    payload["key"] = key
    payload["fields"].update(fields)
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


def make_transport(issues: dict[str, dict], requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.startswith("/rest/api/2/issue/"):
            key = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json=issues[key]) if key in issues else httpx.Response(404)
        params = request.url.params
        wanted = re.search(r"key in \((.*?)\)", params["jql"])
        keys = [k.strip() for k in wanted.group(1).split(",")] if wanted else list(issues)
        found = [issues[k] for k in keys if k in issues]
        start, size = int(params["startAt"]), int(params["maxResults"])
        return httpx.Response(
            200, json={"issues": found[start : start + size], "total": len(found)}
        )

    return httpx.MockTransport(handler)


def make_client(settings, store, transport) -> JiraOnPremClient:
    return JiraOnPremClient(settings, store, transport=transport, sleep=lambda seconds: None)


def with_jira(settings, **updates):
    return settings.model_copy(update={"jira": settings.jira.model_copy(update=updates)})


def test_abstract_client_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        JiraClient()


def test_fake_client_returns_batches() -> None:
    ticket = Ticket("CAE-1", "s", Project("CAE", "VE"), TicketStatus.NEW)

    class Fake(JiraClient):
        def get_ticket(self, key):
            return ticket

        def get_tickets(self, keys):
            return TicketBatch([ticket for _ in keys])

        def search_tickets(self, *, in_sprints_only=False):
            return TicketBatch([ticket])

    client: JiraClient = Fake()
    assert client.get_ticket("CAE-1") is ticket
    assert client.get_tickets(["CAE-1", "CAE-2"]).tickets == [ticket, ticket]
    assert client.search_tickets().failures == []


def test_onprem_is_a_client(configured, store) -> None:
    assert isinstance(JiraOnPremClient(configured, store), JiraClient)


def test_placeholder_url_refused() -> None:
    with pytest.raises(JiraNotConfiguredError, match="jira.base_url"):
        JiraOnPremClient(get_settings())


def test_jql_scope_and_lookback(configured, store) -> None:
    client = JiraOnPremClient(configured, store)
    assert client.build_search_jql() == (
        'project = "CAE" AND cf[12110] = 400 AND issuetype not in ("Sub-task")'
        ' AND (status != "Closed" OR updated >= -30d) ORDER BY key ASC'
    )
    seven = JiraOnPremClient(with_jira(configured, closed_lookback_days=7), store)
    assert "updated >= -7d)" in seven.build_search_jql()


def test_jql_sprint_scope_comes_before_lookback(configured, store) -> None:
    jql = JiraOnPremClient(configured, store).build_search_jql(in_sprints_only=True)
    assert "AND sprint in (openSprints(), futureSprints()) AND (status" in jql
    assert jql.endswith("ORDER BY key ASC")


def test_nothing_excluded_when_the_list_is_empty(configured, store) -> None:
    issues = configured.issues.model_copy(update={"excluded_types": ()})
    client = JiraOnPremClient(configured.model_copy(update={"issues": issues}), store)
    assert "issuetype" not in client.build_search_jql()


def test_multiple_excluded_types_are_quoted(configured, store) -> None:
    issues = configured.issues.model_copy(update={"excluded_types": ("Sub-task", 'Odd"Type')})
    client = JiraOnPremClient(configured.model_copy(update={"issues": issues}), store)
    assert 'issuetype not in ("Sub-task", "Odd\\"Type")' in client.build_search_jql()


def test_explicit_keys_are_not_filtered_by_type(configured, store) -> None:
    requests: list[httpx.Request] = []
    subtask = issue("CAE-7", issuetype={"name": "Sub-task"})
    client = make_client(configured, store, make_transport({"CAE-7": subtask}, requests))
    batch = client.get_tickets(["CAE-7"])
    assert [t.jira_key for t in batch.tickets] == ["CAE-7"]
    assert batch.tickets[0].kind is TicketKind.OTHER
    assert "issuetype" not in requests[0].url.params["jql"]


def test_non_standard_status_is_returned_with_a_finding(configured, store) -> None:
    odd = issue("CAE-3", status={"name": "Implemented"})
    batch = make_client(configured, store, make_transport({"CAE-3": odd}, [])).search_tickets()
    assert batch.failures == []
    assert batch.tickets[0].status is TicketStatus.UNKNOWN
    assert batch.tickets[0].raw_status == "Implemented"
    assert any(f.code is FindingCode.NON_STANDARD_STATUS for f in batch.tickets[0].findings)


def test_team_name_has_no_effect_on_the_query(configured, store) -> None:
    client = JiraOnPremClient(with_jira(configured, team='Bad" OR project = X'), store)
    jql = client.build_search_jql()
    assert "cf[12110] = 400" in jql
    assert "Bad" not in jql and "OR project = X" not in jql


def test_team_id_is_configurable(configured, store) -> None:
    client = JiraOnPremClient(with_jira(configured, team_id=7), store)
    assert "cf[12110] = 7 AND" in client.build_search_jql()


def test_no_credential_read_at_construction(configured, monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("credentials must not be read yet")

    monkeypatch.setattr(jira_onprem, "get_secret", forbidden)
    JiraOnPremClient(configured)


def test_missing_token_explains_how_to_store(configured) -> None:
    client = make_client(configured, InMemorySecretStore(), make_transport({}, []))
    with pytest.raises(MissingSecretError, match="not stored"):
        client.get_ticket("CAE-1")


def test_get_ticket_maps_issue(configured, store) -> None:
    requests: list[httpx.Request] = []
    transport = make_transport({"CAE-1558": issue("CAE-1558")}, requests)
    ticket = make_client(configured, store, transport).get_ticket("CAE-1558")
    assert ticket.jira_key == "CAE-1558"
    assert ticket.kind is TicketKind.REQUEST
    assert requests[0].headers["authorization"] == f"Bearer {TOKEN}"


def test_get_ticket_not_found_names_key(configured, store) -> None:
    client = make_client(configured, store, make_transport({}, []))
    with pytest.raises(JiraApiError, match="CAE-9") as info:
        client.get_ticket("CAE-9")
    assert info.value.kind == "not_found"


def test_get_tickets_chunks_and_dedupes(configured, store) -> None:
    keys = [f"CAE-{n}" for n in range(1, 121)]
    requests: list[httpx.Request] = []
    issues = {key: issue(key) for key in keys}
    client = make_client(configured, store, make_transport(issues, requests))
    batch = client.get_tickets([*keys, "CAE-1"])
    assert len(batch.tickets) == 120 and batch.failures == []
    assert len(requests) == 3
    assert "CAE-1, CAE-2" in requests[0].url.params["jql"]


def test_invalid_key_makes_no_request(configured, store) -> None:
    requests: list[httpx.Request] = []
    client = make_client(configured, store, make_transport({}, requests))
    with pytest.raises(ValueError):
        client.get_tickets(["CAE-1", "x) OR project = Y"])
    assert requests == []


def test_missing_key_is_omitted(configured, store) -> None:
    client = make_client(configured, store, make_transport({"CAE-1": issue("CAE-1")}, []))
    batch = client.get_tickets(["CAE-1", "CAE-2"])
    assert [t.jira_key for t in batch.tickets] == ["CAE-1"]
    assert batch.failures == []


def test_search_isolates_unmappable_tickets(configured, store) -> None:
    bad = issue("CAE-2")
    del bad["fields"]["project"]
    issues = {"CAE-1": issue("CAE-1"), "CAE-2": bad, "CAE-3": issue("CAE-3")}
    batch = make_client(configured, store, make_transport(issues, [])).search_tickets()
    assert [t.jira_key for t in batch.tickets] == ["CAE-1", "CAE-3"]
    assert len(batch.failures) == 1
    assert batch.failures[0].key == "CAE-2" and "project" in batch.failures[0].reason


def test_request_failure_raises_without_partial_batch(configured, store) -> None:
    pages = iter([200, 401])

    def handler(request: httpx.Request) -> httpx.Response:
        if next(pages) == 401:
            return httpx.Response(401)
        return httpx.Response(200, json={"issues": [issue("CAE-1")], "total": 2})

    client = make_client(with_jira(configured, page_size=1), store, httpx.MockTransport(handler))
    with pytest.raises(JiraApiError) as info:
        client.search_tickets()
    assert info.value.kind == "auth"


def test_search_pages_with_configured_size(configured, store) -> None:
    requests: list[httpx.Request] = []
    issues = {f"CAE-{n}": issue(f"CAE-{n}") for n in range(1, 6)}
    client = make_client(
        with_jira(configured, page_size=2), store, make_transport(issues, requests)
    )
    assert len(client.search_tickets().tickets) == 5
    assert len(requests) == 3


def test_end_to_end_task_and_epic_with_only_get(configured, store) -> None:
    epic = issue("CAE-1513")
    epic["fields"]["issuetype"] = {"name": "Epic"}
    task = copy.deepcopy(load("task_epic_link.json"))
    requests: list[httpx.Request] = []
    transport = make_transport({"CAE-1513": epic, "CAE-1628": task}, requests)
    client = make_client(configured, store, transport)

    found = client.search_tickets(in_sprints_only=True)
    parents = client.get_tickets(["CAE-1513"])

    by_key = {t.jira_key: t for t in found.tickets}
    assert by_key["CAE-1628"].kind is TicketKind.TASK
    assert by_key["CAE-1628"].parent_key == "CAE-1513"
    assert by_key["CAE-1513"].kind is TicketKind.REQUEST
    assert parents.tickets[0].jira_key == "CAE-1513"
    assert {request.method for request in requests} == {"GET"}
    assert map_issue(task, configured).parent_key == "CAE-1513"
