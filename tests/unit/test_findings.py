import copy
import json
from pathlib import Path

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.jira_mapping import map_issue
from jira_dashboard.models import FindingCode, TicketKind, TicketStatus

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


@pytest.fixture
def settings():
    return get_settings()


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def link(key: str, issue_type: str, direction: str, phrase: str) -> dict:
    other = {"key": key, "fields": {"issuetype": {"name": issue_type}}}
    link_type = {"name": "T", "inward": "x", "outward": "x", direction: phrase}
    return {"type": link_type, f"{direction}Issue": other}


def task(links=None, epic_link=None) -> dict:
    payload = copy.deepcopy(load("task_epic_link.json"))
    payload["fields"]["customfield_10001"] = epic_link
    payload["fields"]["issuelinks"] = links or []
    return payload


def request(issue_type: str, links=None) -> dict:
    payload = copy.deepcopy(load("issue_cae_1558.json"))
    payload["fields"]["issuetype"] = {"name": issue_type}
    payload["fields"]["issuelinks"] = links or []
    return payload


def codes(ticket) -> list[FindingCode]:
    return [finding.code for finding in ticket.findings]


def test_status_finding_names_the_raw_status(settings) -> None:
    payload = request("Risk")
    payload["fields"]["status"]["name"] = "Implemented"
    ticket = map_issue(payload, settings)
    finding = ticket.findings[0]
    assert finding.code is FindingCode.NON_STANDARD_STATUS
    assert "Implemented" in finding.message
    assert finding.field == "status" and finding.suggestion


def test_official_status_has_no_status_finding(settings) -> None:
    assert FindingCode.NON_STANDARD_STATUS not in codes(map_issue(request("Risk"), settings))


def test_task_with_epic_link_alone_is_not_flagged(settings) -> None:
    ticket = map_issue(task(epic_link="CAE-1513"), settings)
    assert ticket.parent_key == "CAE-1513"
    assert FindingCode.TASK_WITHOUT_PARENT not in codes(ticket)


def test_task_child_of_a_risk_is_not_flagged(settings) -> None:
    ticket = map_issue(task([link("CAE-1558", "Risk", "inward", "is child of")]), settings)
    assert ticket.parent_key == "CAE-1558"
    assert FindingCode.TASK_WITHOUT_PARENT not in codes(ticket)


@pytest.mark.parametrize(
    "links",
    [
        [link("CAE-1", "Issue", "outward", "mentions"), link("CAE-2", "Task", "outward", "clones")],
        [link("CAE-3", "Task", "inward", "is blocked by")],
        [],
    ],
    ids=["mentions-and-clones", "blocked-by", "no-links"],
)
def test_task_without_a_parent_is_flagged(links, settings) -> None:
    ticket = map_issue(task(links), settings)
    assert ticket.parent_key is None
    flagged = [f for f in ticket.findings if f.code is FindingCode.TASK_WITHOUT_PARENT]
    assert len(flagged) == 1 and flagged[0].suggestion


def test_requests_never_get_the_parent_finding(settings) -> None:
    assert FindingCode.TASK_WITHOUT_PARENT not in codes(map_issue(request("Risk"), settings))
    assert map_issue(request("Risk"), settings).kind is TicketKind.REQUEST


@pytest.mark.parametrize(
    ("issue_type", "direction", "phrase"),
    [("Risk", "inward", "is child of"), ("Issue", "outward", "created by")],
)
def test_wrong_epic_link_is_flagged_and_not_used_as_parent(
    issue_type, direction, phrase, settings
) -> None:
    ticket = map_issue(request(issue_type, [link("CAE-1513", "Epic", direction, phrase)]), settings)
    assert ticket.parent_key is None
    flagged = [f for f in ticket.findings if f.code is FindingCode.REQUEST_WRONG_EPIC_LINK]
    assert len(flagged) == 1
    assert flagged[0].related_key == "CAE-1513"
    assert phrase in flagged[0].message and "is caused by" in flagged[0].suggestion


def test_correct_epic_link_is_not_flagged(settings) -> None:
    ticket = map_issue(
        request("Risk", [link("CAE-1513", "Epic", "inward", "is caused by")]), settings
    )
    assert ticket.parent_key == "CAE-1513"
    assert FindingCode.REQUEST_WRONG_EPIC_LINK not in codes(ticket)


@pytest.mark.parametrize(
    "links",
    [
        [],
        [link("CAE-9", "Task", "inward", "is child of")],
        [link("CAE-1513", "Epic", "inward", "mentions")],
        [link("CAE-1513", "Epic", "inward", "is mentioned by")],
    ],
    ids=["no-links", "wrong-target-type", "mentions", "mentioned-by"],
)
def test_other_links_do_not_flag_a_request(links, settings) -> None:
    assert codes(map_issue(request("Risk", links), settings)) == []


def test_duplicate_wrong_links_are_reported_once(settings) -> None:
    links = [
        link("CAE-1513", "Epic", "inward", "is child of"),
        link("CAE-1513", "Epic", "inward", "is child of"),
        link("CAE-1514", "Epic", "inward", "created by"),
    ]
    ticket = map_issue(request("Risk", links), settings)
    assert [f.related_key for f in ticket.findings] == ["CAE-1513", "CAE-1514"]


def test_epic_never_gets_link_findings(settings) -> None:
    links = [link("CAE-2", "Epic", "inward", "is child of")]
    assert codes(map_issue(request("Epic", links), settings)) == []


def test_findings_never_fail_the_ticket_and_are_stable(settings) -> None:
    payload = task()
    payload["fields"]["status"]["name"] = "Implemented"
    first = map_issue(payload, settings)
    second = map_issue(copy.deepcopy(payload), settings)
    assert first.findings == second.findings
    assert codes(first) == [FindingCode.NON_STANDARD_STATUS, FindingCode.TASK_WITHOUT_PARENT]
    assert first.status is TicketStatus.UNKNOWN


def test_absent_optional_data_is_not_a_finding(settings) -> None:
    payload = request("Risk")
    for name in ("assignee", "reporter", "customfield_12112", "customfield_12113", "description"):
        payload["fields"][name] = None
    payload["fields"].pop("timeoriginalestimate", None)
    ticket = map_issue(payload, settings)
    assert ticket.estimated_effort is None and ticket.requester is None
    assert ticket.assignee is None
    assert ticket.findings == ()
