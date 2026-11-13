import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime
from typing import Any

from jira_dashboard.config.settings import IssueSettings, RequesterTemplate, Settings
from jira_dashboard.integrations.jira_findings import (
    iter_links,
    sort_findings,
    status_finding,
    task_parent_finding,
    wrong_epic_link_findings,
)
from jira_dashboard.models import (
    Domain,
    Finding,
    FindingCode,
    Project,
    Sprint,
    Ticket,
    TicketKind,
    TicketStatus,
    User,
)

_LEGACY_PAIR = re.compile(r"(\w+)=(.*?)(?=,\w+=|$)", re.DOTALL)
_TRAILING_PUNCTUATION = ".,;:"


class TicketMappingError(Exception):
    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"Cannot map ticket {key}: {reason}")
        self.key = key
        self.reason = reason


def seconds_to_days(seconds: float | None, hours_per_day: float) -> float | None:
    if seconds is None:
        return None
    return float(seconds) / (hours_per_day * 3600)


def parse_timestamp(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def parse_date(text: str | None) -> date | None:
    return date.fromisoformat(text[:10]) if text else None


def map_user(data: Mapping[str, Any] | None) -> User | None:
    if not data:
        return None
    username = data.get("name") or data.get("key")
    if not username:
        return None
    return User(
        username=username,
        display_name=data.get("displayName") or username,
        email=data.get("emailAddress"),
    )


def _clean(value: Any) -> Any:
    return None if value in (None, "", "<null>") else value


def _sprint_from_dict(data: Mapping[str, Any]) -> Sprint:
    return Sprint(
        id=int(data["id"]),
        name=data["name"],
        state=str(data.get("state", "")).upper(),
        start_date=parse_date(_clean(data.get("startDate"))),
        end_date=parse_date(_clean(data.get("endDate"))),
    )


def _sprint_from_legacy(text: str) -> Sprint:
    body = text[text.index("[") + 1 : text.rindex("]")]
    return _sprint_from_dict(dict(_LEGACY_PAIR.findall(body)))


def parse_sprint(value: Any) -> Sprint | None:
    if value in (None, "", []):
        return None
    items = value if isinstance(value, list) else [value]
    sprints = [
        _sprint_from_legacy(item) if isinstance(item, str) else _sprint_from_dict(item)
        for item in items
    ]
    active = [s for s in sprints if s.state == "ACTIVE"]
    return active[0] if active else max(sprints, key=lambda s: s.id)


def extract_requester(description: str | None, template: RequesterTemplate) -> str | None:
    if not description:
        return None
    pattern = re.compile(
        r"\{panel:[^}]*?title=" + re.escape(template.panel_title) + r"[^}]*\}(.*?)\{panel\}",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(description)
    if not match:
        return None
    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if not lines:
        return None
    requester = lines[0].rstrip(_TRAILING_PUNCTUATION).strip()
    placeholders = {p.lower() for p in template.placeholders}
    if not requester or requester.lower() in placeholders:
        return None
    return requester


def map_kind(issue_type: str | None, issues: IssueSettings) -> TicketKind:
    name = (issue_type or "").lower()
    if name in {t.lower() for t in issues.request_types}:
        return TicketKind.REQUEST
    if name in {t.lower() for t in issues.task_types}:
        return TicketKind.TASK
    return TicketKind.OTHER


def _linked_keys(
    fields: Mapping[str, Any], phrases: Sequence[str], target_types: set[str]
) -> list[str]:
    wanted = {phrase.lower() for phrase in phrases}
    return [
        link.key
        for link in iter_links(fields)
        if link.phrase.lower() in wanted and link.issue_type.lower() in target_types
    ]


def map_parent(fields: Mapping[str, Any], kind: TicketKind, settings: Settings) -> str | None:
    issues = settings.issues
    epic_type = issues.epic_type.lower()
    own_type = ((fields.get("issuetype") or {}).get("name") or "").lower()

    if kind is TicketKind.TASK:
        epic_field = settings.fields.epic_link
        epic_key = fields.get(epic_field) if epic_field else None
        if isinstance(epic_key, str) and epic_key.strip():
            return epic_key.strip()
        targets = {t.lower() for t in issues.request_types} - {epic_type}
        candidates = _linked_keys(fields, issues.task_parent_phrases, targets)
    elif kind is TicketKind.REQUEST and own_type != epic_type:
        candidates = _linked_keys(fields, issues.request_parent_phrases, {epic_type})
    else:
        return None
    return min(candidates) if candidates else None


def _names(items: Sequence[Mapping[str, Any]] | None) -> tuple[str, ...]:
    return tuple(item["name"] for item in items or [])


def _dyson_projects(value: Any) -> tuple[str, ...]:
    """Option names of the multi-select field; blanks dropped, repeats kept once."""
    if not isinstance(value, list | tuple):
        return ()
    names: list[str] = []
    for item in value:
        name = item.get("value") if isinstance(item, Mapping) else item
        if isinstance(name, str) and (name := name.strip()) and name not in names:
            names.append(name)
    return tuple(names)


def map_issue(payload: Mapping[str, Any], settings: Settings) -> Ticket:
    key = str(payload.get("key", "?"))
    try:
        return _map_issue(payload, settings)
    except TicketMappingError:
        raise
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise TicketMappingError(key, f"{type(exc).__name__}: {exc}") from exc


def _read(parser, value: Any, field_name: str, findings: list[Finding]) -> Any:
    """Parse a value; on failure return None (unknown) and record an INVALID_VALUE finding."""
    try:
        return parser(value)
    except ValueError, TypeError, KeyError, AttributeError, IndexError:
        findings.append(
            Finding(
                FindingCode.INVALID_VALUE,
                f"The {field_name} value could not be read",
                field=field_name,
                suggestion=f"Correct the {field_name} in Jira",
            )
        )
        return None


def _map_issue(payload: Mapping[str, Any], settings: Settings) -> Ticket:
    key = payload["key"]
    fields = payload["fields"]
    ids = settings.fields
    hours = settings.working_time.hours_per_day
    findings: list[Finding] = []

    simulation = fields.get(ids.simulation_type)
    simulation_text = simulation.get("value") if isinstance(simulation, Mapping) else simulation
    issue_type = (fields.get("issuetype") or {}).get("name")
    kind = map_kind(issue_type, settings.issues)
    description = fields.get("description")
    project = fields["project"]
    summary = fields["summary"]
    raw_status = (fields.get("status") or {}).get("name")
    status = TicketStatus.from_jira(raw_status)
    parent_key = map_parent(fields, kind, settings)

    ticket_findings = [
        status_finding(status, raw_status),
        task_parent_finding(kind, parent_key),
        *wrong_epic_link_findings(fields, kind, issue_type, settings),
    ]

    def days(value: Any) -> float | None:
        return seconds_to_days(value, hours)

    ticket = Ticket(
        jira_key=key,
        summary=summary,
        project=Project(key=project["key"], name=project.get("name", project["key"])),
        status=status,
        description=description,
        issue_type=issue_type,
        domain=Domain.from_simulation_type(simulation_text),
        request_drivers=_names(fields.get(ids.request_drivers)),
        dyson_projects=_dyson_projects(fields.get(ids.dyson_project_list)),
        assignee=map_user(fields.get("assignee")),
        reporter=map_user(fields.get("reporter")),
        requester=extract_requester(description, settings.requester),
        priority=(fields.get("priority") or {}).get("name"),
        target_start_date=_read(parse_date, fields.get(ids.target_start), "target start", findings),
        target_end_date=_read(parse_date, fields.get(ids.target_end), "target end", findings),
        created_date=_read(parse_timestamp, fields.get("created"), "created", findings),
        updated_date=_read(parse_timestamp, fields.get("updated"), "updated", findings),
        sprint=_read(parse_sprint, fields.get(ids.sprint), "sprint", findings),
        estimated_effort=_read(days, fields.get(ids.estimated_effort), "estimate", findings),
        remaining_effort=_read(days, fields.get(ids.remaining_effort), "remaining", findings),
        jira_url=f"{settings.jira.base_url}/browse/{key}",
        kind=kind,
        parent_key=parent_key,
        raw_status=raw_status,
    )
    all_findings = [f for f in ticket_findings if f is not None] + findings
    return replace(ticket, findings=sort_findings(all_findings))
