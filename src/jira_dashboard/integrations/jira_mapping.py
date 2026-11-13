import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from jira_dashboard.config.settings import IssueSettings, RequesterTemplate, Settings
from jira_dashboard.models import (
    Domain,
    Project,
    Sprint,
    Ticket,
    TicketKind,
    TicketStatus,
    User,
)

LINK_PARENT_TYPES = frozenset({"risk", "issue"})
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


def map_parent(fields: Mapping[str, Any], kind: TicketKind, settings: Settings) -> str | None:
    if kind is not TicketKind.TASK:
        return None
    epic_field = settings.fields.epic_link
    epic_key = fields.get(epic_field) if epic_field else None
    if isinstance(epic_key, str) and epic_key.strip():
        return epic_key.strip()

    phrases = {p.lower() for p in settings.issues.parent_link_phrases}
    candidates: list[str] = []
    for link in fields.get("issuelinks") or []:
        if "inwardIssue" in link:
            other, phrase = link["inwardIssue"], link["type"]["inward"]
        elif "outwardIssue" in link:
            other, phrase = link["outwardIssue"], link["type"]["outward"]
        else:
            continue
        other_type = other.get("fields", {}).get("issuetype", {}).get("name", "")
        if phrase.lower() in phrases and other_type.lower() in LINK_PARENT_TYPES:
            candidates.append(other["key"])
    return min(candidates) if candidates else None


def _names(items: Sequence[Mapping[str, Any]] | None) -> tuple[str, ...]:
    return tuple(item["name"] for item in items or [])


def map_issue(payload: Mapping[str, Any], settings: Settings) -> Ticket:
    key = str(payload.get("key", "?"))
    try:
        return _map_issue(payload, settings)
    except TicketMappingError:
        raise
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise TicketMappingError(key, f"{type(exc).__name__}: {exc}") from exc


def _map_issue(payload: Mapping[str, Any], settings: Settings) -> Ticket:
    key = payload["key"]
    fields = payload["fields"]
    ids = settings.fields
    hours = settings.working_time.hours_per_day

    simulation = fields.get(ids.simulation_type)
    simulation_text = simulation.get("value") if isinstance(simulation, Mapping) else simulation
    issue_type = (fields.get("issuetype") or {}).get("name")
    kind = map_kind(issue_type, settings.issues)
    description = fields.get("description")
    project = fields["project"]

    return Ticket(
        jira_key=key,
        summary=fields["summary"],
        project=Project(key=project["key"], name=project.get("name", project["key"])),
        status=TicketStatus.from_jira(fields["status"]["name"]),
        description=description,
        issue_type=issue_type,
        domain=Domain.from_simulation_type(simulation_text),
        request_drivers=_names(fields.get(ids.request_drivers)),
        assignee=map_user(fields.get("assignee")),
        reporter=map_user(fields.get("reporter")),
        requester=extract_requester(description, settings.requester),
        priority=(fields.get("priority") or {}).get("name"),
        target_start_date=parse_date(fields.get(ids.target_start)),
        target_end_date=parse_date(fields.get(ids.target_end)),
        created_date=parse_timestamp(fields.get("created")),
        updated_date=parse_timestamp(fields.get("updated")),
        sprint=parse_sprint(fields.get(ids.sprint)),
        estimated_effort=seconds_to_days(fields.get(ids.estimated_effort), hours),
        remaining_effort=seconds_to_days(fields.get(ids.remaining_effort), hours),
        jira_url=f"{settings.jira.base_url}/browse/{key}",
        kind=kind,
        parent_key=map_parent(fields, kind, settings),
    )
