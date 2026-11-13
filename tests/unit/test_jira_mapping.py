import copy
import json
from datetime import UTC, date, timedelta
from pathlib import Path

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.jira_mapping import (
    TicketMappingError,
    extract_requester,
    map_issue,
    map_kind,
    map_parent,
    map_user,
    parse_sprint,
    parse_timestamp,
    seconds_to_days,
)
from jira_dashboard.models import Domain, FindingCode, TicketKind, TicketStatus

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


PIC_PANEL = "{panel:title=PIC (Requester - Full Name)|titleBGColor=#ffffcc}"

LEGACY = (
    "com.atlassian.greenhopper.service.sprint.Sprint@1a[id=12,rapidViewId=3,state=ACTIVE,"
    "name={name},startDate=2026-11-02T09:00:00.000+08:00,"
    "endDate=2026-11-16T18:00:00.000+08:00,completeDate=<null>,sequence=12]"
)


def test_seconds_to_days() -> None:
    assert seconds_to_days(115200, 8) == 4.0
    assert seconds_to_days(None, 8) is None


def test_timestamp_offset() -> None:
    parsed = parse_timestamp("2026-10-28T10:46:00.000+0800")
    assert (parsed.hour, parsed.minute) == (10, 46)
    assert parsed.utcoffset() == timedelta(hours=8)
    assert parsed.tzinfo is not None and parsed.tzinfo != UTC
    assert parse_timestamp(None) is None


def test_map_user() -> None:
    user = map_user({"name": "cchong", "displayName": "CY Chong"})
    assert (user.username, user.display_name, user.email) == ("cchong", "CY Chong", None)
    assert map_user(None) is None


@pytest.mark.parametrize("name", ["Static Sprint (Wk45- 46 26)", "Sprint A, B (x)", "Plain"])
def test_parse_sprint_legacy_names(name: str) -> None:
    sprint = parse_sprint([LEGACY.format(name=name)])
    assert (sprint.id, sprint.name, sprint.state) == (12, name, "ACTIVE")
    assert sprint.end_date == date(2026, 11, 16)


def test_parse_sprint_prefers_active_and_handles_null_dates() -> None:
    closed = LEGACY.format(name="Old").replace("ACTIVE", "CLOSED").replace("id=12", "id=20")
    closed = closed.replace("endDate=2026-11-16T18:00:00.000+08:00", "endDate=<null>")
    active = LEGACY.format(name="Now")
    assert parse_sprint([closed, active]).name == "Now"
    assert parse_sprint([closed]).end_date is None


def test_parse_sprint_latest_when_none_active() -> None:
    first = LEGACY.format(name="A").replace("ACTIVE", "CLOSED")
    second = LEGACY.format(name="B").replace("ACTIVE", "CLOSED").replace("id=12", "id=30")
    assert parse_sprint([first, second]).name == "B"


def test_parse_sprint_structured_and_empty() -> None:
    sprint = parse_sprint([{"id": 5, "name": "S", "state": "active", "endDate": "2026-11-16"}])
    assert (sprint.id, sprint.state, sprint.end_date) == (5, "ACTIVE", date(2026, 11, 16))
    assert parse_sprint(None) is None
    assert parse_sprint([]) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            PIC_PANEL + "\nMohamad Faizal.\n{panel}",
            "Mohamad Faizal",
        ),
        ("{panel:title=PIC (Requester - Full Name)}\nRequester\n{panel}", None),
        ("{panel:title=PIC (Requester - Full Name)}\n\n{panel}", None),
        ("{panel:title=Background}\nPeople\n{panel}", None),
        (None, None),
    ],
)
def test_extract_requester(text, expected, settings) -> None:
    assert extract_requester(text, settings.requester) == expected


def test_map_kind(settings) -> None:
    assert map_kind("Risk", settings.issues) is TicketKind.REQUEST
    assert map_kind("Epic", settings.issues) is TicketKind.REQUEST
    assert map_kind("Task", settings.issues) is TicketKind.TASK
    assert map_kind("Bug", settings.issues) is TicketKind.OTHER


def link(key, issue_type, direction, phrase):
    other = {"key": key, "fields": {"issuetype": {"name": issue_type}}}
    type_ = {"name": "T", "inward": "x", "outward": "x"}
    type_[direction] = phrase
    return {"type": type_, f"{direction}Issue": other}


def test_parent_epic_link_wins(settings) -> None:
    fields = {
        "customfield_10001": "CAE-1513",
        "issuelinks": [link("CAE-1558", "Risk", "inward", "is child of")],
    }
    assert map_parent(fields, TicketKind.TASK, settings) == "CAE-1513"


@pytest.mark.parametrize(
    ("direction", "phrase", "issue_type", "expected"),
    [
        ("inward", "is child of", "Risk", "CAE-1558"),
        ("outward", "Is Child Of", "Issue", "CAE-1558"),
        ("inward", "is caused by", "Risk", None),
        ("inward", "mentions", "Risk", None),
        ("inward", "relates to", "Risk", None),
        ("inward", "is child of", "Task", None),
        ("inward", "is child of", "Epic", None),
    ],
)
def test_parent_from_links(direction, phrase, issue_type, expected, settings) -> None:
    fields = {"issuelinks": [link("CAE-1558", issue_type, direction, phrase)]}
    assert map_parent(fields, TicketKind.TASK, settings) == expected


@pytest.mark.parametrize("own_type", ["Risk", "Issue"])
def test_risk_or_issue_caused_by_epic(own_type, settings) -> None:
    fields = {
        "issuetype": {"name": own_type},
        "issuelinks": [link("CAE-1513", "Epic", "inward", "is caused by")],
    }
    assert map_parent(fields, TicketKind.REQUEST, settings) == "CAE-1513"


@pytest.mark.parametrize(
    ("phrase", "target"),
    [("is child of", "Epic"), ("is caused by", "Risk"), ("mentions", "Epic")],
)
def test_request_ignores_other_links(phrase, target, settings) -> None:
    fields = {
        "issuetype": {"name": "Risk"},
        "issuelinks": [link("CAE-1", target, "inward", phrase)],
    }
    assert map_parent(fields, TicketKind.REQUEST, settings) is None


def test_epic_never_has_a_parent(settings) -> None:
    fields = {
        "issuetype": {"name": "Epic"},
        "issuelinks": [link("CAE-1", "Epic", "inward", "is caused by")],
    }
    assert map_parent(fields, TicketKind.REQUEST, settings) is None


def mention(key, issue_type, direction):
    phrase = {"inward": "is mentioned by", "outward": "mentions"}[direction]
    return link(key, issue_type, direction, phrase)


def test_mentions_never_define_a_parent(settings) -> None:
    risk = {
        "issuetype": {"name": "Risk"},
        "issuelinks": [
            mention("LDT-1497", "Issue", "outward"),
            mention("LDT-1597", "Issue", "outward"),
            mention("CAE-1559", "Task", "inward"),
        ],
    }
    task = {"issuetype": {"name": "Task"}, "issuelinks": [mention("CAE-1558", "Risk", "outward")]}
    assert map_parent(risk, TicketKind.REQUEST, settings) is None
    assert map_parent(task, TicketKind.TASK, settings) is None


def test_parent_lowest_key_and_requests_have_none(settings) -> None:
    links = [
        link("CAE-1592", "Issue", "inward", "is child of"),
        link("CAE-1558", "Risk", "inward", "is child of"),
    ]
    assert map_parent({"issuelinks": links}, TicketKind.TASK, settings) == "CAE-1558"
    assert map_parent({"customfield_10001": "CAE-1"}, TicketKind.REQUEST, settings) is None


def test_map_risk_fixture(settings) -> None:
    ticket = map_issue(load("issue_cae_1558.json"), settings)
    assert ticket.jira_key == "CAE-1558"
    assert ticket.status is TicketStatus.IN_PROGRESS
    assert ticket.issue_type == "Risk"
    assert ticket.priority == "Major"
    assert ticket.kind is TicketKind.REQUEST
    assert ticket.domain is Domain.STATIC
    assert ticket.request_drivers == ("Risk",)
    assert ticket.requester == "Mohamad Faizal"
    assert ticket.target_start_date == date(2026, 10, 30)
    assert ticket.target_end_date == date(2026, 11, 11)
    assert ticket.created_date.hour == 10
    assert ticket.sprint is None
    assert ticket.estimated_effort is None
    assert ticket.parent_key is None
    assert ticket.assignee.display_name == "CY Chong"
    assert ticket.jira_url.endswith("/browse/CAE-1558")


def test_map_task_with_epic_link(settings) -> None:
    ticket = map_issue(load("task_epic_link.json"), settings)
    assert ticket.kind is TicketKind.TASK
    assert ticket.parent_key == "CAE-1513"
    assert ticket.estimated_effort == 4.0
    assert ticket.remaining_effort == 4.0
    assert ticket.sprint.name == "Static Sprint (Wk45- 46 26)"
    assert ticket.sprint.end_date == date(2026, 11, 16)
    assert ticket.domain is Domain.DYNAMIC
    assert ticket.requester is None
    assert ticket.reporter.email is None


def test_map_task_with_link_and_missing_fields(settings) -> None:
    ticket = map_issue(load("task_risk_link.json"), settings)
    assert ticket.parent_key == "CAE-1558"
    assert ticket.domain is Domain.UNSPECIFIED
    assert ticket.assignee is None
    assert ticket.estimated_effort == 2.0
    assert ticket.status is TicketStatus.PLANNED


def test_reconfigured_field_id(settings) -> None:
    payload = load("issue_cae_1558.json")
    payload["fields"]["customfield_99999"] = "2026-12-01"
    fields = settings.fields.model_copy(update={"target_end": "customfield_99999"})
    changed = settings.model_copy(update={"fields": fields})
    assert map_issue(payload, changed).target_end_date == date(2026, 12, 1)


def test_unsupported_status_maps_to_unknown(settings) -> None:
    payload = load("issue_cae_1558.json")
    payload["fields"]["status"]["name"] = "Implemented"
    ticket = map_issue(payload, settings)
    assert ticket.status is TicketStatus.UNKNOWN
    assert ticket.raw_status == "Implemented"
    assert ticket.summary and ticket.target_end_date == date(2026, 11, 11)


def test_official_status_keeps_raw_name(settings) -> None:
    ticket = map_issue(load("issue_cae_1558.json"), settings)
    assert ticket.status is TicketStatus.IN_PROGRESS
    assert ticket.raw_status == "In Progress"


@pytest.mark.parametrize("missing", ["project", "summary"])
def test_unusable_payload_names_ticket(missing, settings) -> None:
    payload = load("issue_cae_1558.json")
    del payload["fields"][missing]
    with pytest.raises(TicketMappingError) as info:
        map_issue(payload, settings)
    assert info.value.key == "CAE-1558"
    assert "CAE-1558" in str(info.value)


def test_missing_key_or_fields_is_an_error(settings) -> None:
    with pytest.raises(TicketMappingError):
        map_issue({"fields": {}}, settings)
    with pytest.raises(TicketMappingError, match="CAE-1"):
        map_issue({"key": "CAE-1"}, settings)


def test_missing_optional_fields_map_as_unknown(settings) -> None:
    payload = load("task_risk_link.json")
    for name in ("priority", "assignee", "reporter", "customfield_10000", "timeoriginalestimate"):
        payload["fields"].pop(name, None)
    payload["fields"].pop("status")
    ticket = map_issue(payload, settings)
    assert ticket.priority is None and ticket.assignee is None and ticket.sprint is None
    assert ticket.estimated_effort is None
    assert ticket.status is TicketStatus.UNKNOWN and ticket.raw_status is None


def test_invalid_target_end_is_unknown_with_finding(settings) -> None:
    payload = load("issue_cae_1558.json")
    payload["fields"]["customfield_12113"] = "31/13/2026"
    ticket = map_issue(payload, settings)
    assert ticket.target_end_date is None
    assert ticket.target_start_date == date(2026, 10, 30)
    invalid = [f for f in ticket.findings if f.code is FindingCode.INVALID_VALUE]
    assert [f.field for f in invalid] == ["target end"]
    assert "31/13" not in invalid[0].message


def test_invalid_timestamp_and_estimate_keep_the_ticket(settings) -> None:
    payload = load("task_epic_link.json")
    payload["fields"]["created"] = "yesterday"
    payload["fields"]["timeoriginalestimate"] = "four days"
    ticket = map_issue(payload, settings)
    assert ticket.created_date is None and ticket.estimated_effort is None
    assert ticket.remaining_effort == 4.0
    fields = {f.field for f in ticket.findings if f.code is FindingCode.INVALID_VALUE}
    assert fields == {"created", "estimate"}


def test_unreadable_sprint_has_no_sprint_and_a_finding(settings) -> None:
    payload = load("task_epic_link.json")
    payload["fields"]["customfield_10000"] = ["not a sprint at all"]
    ticket = map_issue(payload, settings)
    assert ticket.sprint is None
    assert any(f.field == "sprint" for f in ticket.findings)


def test_payload_unchanged(settings) -> None:
    payload = load("task_epic_link.json")
    before = copy.deepcopy(payload)
    map_issue(payload, settings)
    assert payload == before
