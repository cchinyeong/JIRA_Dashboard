from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from jira_dashboard.config.settings import Settings
from jira_dashboard.integrations.jira_http import FieldFinding
from jira_dashboard.integrations.jira_mapping import TicketMappingError, map_issue

EXPECTED_TYPES = {
    "CAE-1513": "Epic",
    "CAE-1558": "Risk",
    "CAE-1592": "Issue",
    "CAE-1628": "Task",
}


@dataclass(frozen=True)
class TicketReport:
    key: str
    issue_type: str | None
    expected_type: str | None
    mapped: bool
    error: str | None = None
    details: Mapping[str, str] = field(default_factory=dict)
    link_texts: tuple[str, ...] = ()
    epic_shape: str = "none"
    sprint_format: str = "none"

    @property
    def type_mismatch(self) -> bool:
        return self.expected_type is not None and self.issue_type != self.expected_type


def _shape(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, str):
        return "str"
    if isinstance(value, Mapping):
        return "dict"
    return type(value).__name__


def _sprint_format(value: Any) -> str:
    if value in (None, "", []):
        return "none"
    items = value if isinstance(value, list) else [value]
    kinds = {"legacy" if isinstance(item, str) else "structured" for item in items}
    return kinds.pop() if len(kinds) == 1 else "mixed"


def _link_texts(links: list[Mapping[str, Any]]) -> tuple[str, ...]:
    texts = []
    for link in links:
        link_type = link.get("type") or {}
        for side, phrase in (("inwardIssue", "inward"), ("outwardIssue", "outward")):
            other = link.get(side)
            if other:
                other_type = ((other.get("fields") or {}).get("issuetype") or {}).get("name")
                texts.append(f"{link_type.get(phrase)} -> {other.get('key')} ({other_type})")
    return tuple(texts)


def analyse_ticket(
    payload: Mapping[str, Any], settings: Settings, expected_type: str | None = None
) -> TicketReport:
    fields = payload.get("fields") or {}
    epic_field = settings.fields.epic_link
    common = {
        "key": str(payload.get("key", "?")),
        "issue_type": (fields.get("issuetype") or {}).get("name"),
        "expected_type": expected_type,
        "link_texts": _link_texts(fields.get("issuelinks") or []),
        "epic_shape": _shape(fields.get(epic_field)) if epic_field else "not configured",
        "sprint_format": _sprint_format(fields.get(settings.fields.sprint)),
    }
    try:
        ticket = map_issue(payload, settings)
    except TicketMappingError as exc:
        return TicketReport(mapped=False, error=exc.reason, **common)
    details = {
        "kind": ticket.kind.value,
        "status": ticket.status.value,
        "domain": ticket.domain.value,
        "request drivers": ", ".join(ticket.request_drivers) or "none",
        "parent": ticket.parent_key or "none",
        "estimate (days)": "unknown"
        if ticket.estimated_effort is None
        else f"{ticket.estimated_effort:g}",
        "remaining (days)": "unknown"
        if ticket.remaining_effort is None
        else f"{ticket.remaining_effort:g}",
        "requester found": "yes" if ticket.requester else "no",
        "sprint": (
            f"{ticket.sprint.state}, ends {ticket.sprint.end_date or 'unknown'}"
            if ticket.sprint
            else "none"
        ),
        "target": (
            f"{ticket.target_start_date or 'unknown'} to {ticket.target_end_date or 'unknown'}"
        ),
    }
    return TicketReport(mapped=True, details=details, **common)


def format_report(
    reports: list[TicketReport],
    findings: list[FieldFinding],
    errors: Mapping[str, str],
    notes: list[str],
) -> str:
    lines = ["Field check"]
    if not findings:
        lines.append("  not available")
    for item in findings:
        suffix = f" (Jira name: {item.jira_name})" if item.jira_name else ""
        lines.append(f"  {item.setting}: {item.field_id} -> {item.status}{suffix}")

    for report in reports:
        lines.append("")
        lines.append(f"{report.key} ({report.issue_type or 'unknown type'})")
        if report.type_mismatch:
            lines.append(f"  expected type {report.expected_type}, got {report.issue_type}")
        if report.mapped:
            lines.extend(f"  {name}: {value}" for name, value in report.details.items())
        else:
            lines.append(f"  NOT MAPPED: {report.error}")
        lines.append(f"  epic link value: {report.epic_shape}")
        lines.append(f"  sprint format: {report.sprint_format}")
        for text in report.link_texts:
            lines.append(f"  link: {text}")

    for key, message in errors.items():
        lines.append("")
        lines.append(f"{key}: NOT RETRIEVED - {message}")

    lines.append("")
    lines.append(
        "Observed link texts: "
        + (
            ", ".join(
                sorted({text.split(" -> ")[0] for report in reports for text in report.link_texts})
            )
            or "none"
        )
    )
    lines.extend(notes)
    return "\n".join(lines)
