import json
from datetime import date
from pathlib import Path

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.jira_mapping import map_issue
from jira_dashboard.models import Domain, TicketKind, TicketStatus

LIVE = Path(__file__).parent / "fixtures" / "live"
FILES = sorted(LIVE.glob("*.json"))

OBSERVED = {
    "CAE-1513": (TicketKind.REQUEST, TicketStatus.PLANNED, Domain.DYNAMIC, ("Verification",), None),
    "CAE-1558": (TicketKind.REQUEST, TicketStatus.IN_PROGRESS, Domain.STATIC, ("Risk",), None),
    "CAE-1592": (TicketKind.REQUEST, TicketStatus.CLOSED, Domain.DYNAMIC, ("Issue",), None),
    "CAE-1628": (
        TicketKind.TASK,
        TicketStatus.NEW,
        Domain.DYNAMIC,
        ("Verification",),
        "CAE-1513",
    ),
}

pytestmark = pytest.mark.skipif(not FILES, reason="no sanitised live fixtures present")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


def load(key: str) -> dict:
    path = LIVE / f"{key}.json"
    if not path.exists():
        pytest.skip(f"{key} fixture not present")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_live_fixture_maps(path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert map_issue(payload, get_settings()).jira_key == payload["key"]


@pytest.mark.parametrize("key", OBSERVED)
def test_observed_shapes(key) -> None:
    kind, status, domain, drivers, parent = OBSERVED[key]
    ticket = map_issue(load(key), get_settings())
    assert ticket.kind is kind
    assert ticket.status is status
    assert ticket.domain is domain
    assert ticket.request_drivers == drivers
    assert ticket.parent_key == parent
    assert ticket.findings == ()
    assert ticket.raw_status


def test_risk_mention_links_do_not_create_a_parent() -> None:
    payload = load("CAE-1558")
    links = payload["fields"]["issuelinks"]
    assert any(link["type"]["outward"] == "mentions" for link in links)
    assert map_issue(payload, get_settings()).parent_key is None


def test_task_in_future_sprint_uses_epic_link() -> None:
    ticket = map_issue(load("CAE-1628"), get_settings())
    assert ticket.sprint.state == "FUTURE"
    assert ticket.sprint.end_date == date(2026, 11, 30)
    assert ticket.estimated_effort is None
