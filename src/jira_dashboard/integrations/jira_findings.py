from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from jira_dashboard.config.settings import Settings
from jira_dashboard.models import Finding, FindingCode, TicketKind, TicketStatus


@dataclass(frozen=True, slots=True)
class LinkRef:
    phrase: str
    key: str
    issue_type: str


def iter_links(fields: Mapping[str, Any]) -> Iterator[LinkRef]:
    """Yield each issue link as seen from this ticket: the text Jira shows and the other end."""
    for link in fields.get("issuelinks") or []:
        link_type = link.get("type") or {}
        for side, direction in (("inwardIssue", "inward"), ("outwardIssue", "outward")):
            other = link.get(side)
            phrase = link_type.get(direction)
            if other and phrase and other.get("key"):
                other_type = ((other.get("fields") or {}).get("issuetype") or {}).get("name")
                yield LinkRef(phrase, other["key"], other_type or "")


def status_finding(status: TicketStatus, raw_status: str | None) -> Finding | None:
    if status is not TicketStatus.UNKNOWN:
        return None
    shown = f"'{raw_status}'" if raw_status else "(missing)"
    return Finding(
        FindingCode.NON_STANDARD_STATUS,
        f"Status {shown} is not one of the workflow statuses",
        field="status",
        suggestion="Change the ticket to a standard status",
    )


def task_parent_finding(kind: TicketKind, parent_key: str | None) -> Finding | None:
    if kind is not TicketKind.TASK or parent_key:
        return None
    return Finding(
        FindingCode.TASK_WITHOUT_PARENT,
        "Task has no parent: no Epic Link and no 'is child of' link to a Risk or Issue",
        field="parent",
        suggestion="Link the Task to its Risk or Issue, or set its Epic Link",
    )


def wrong_epic_link_findings(
    fields: Mapping[str, Any], kind: TicketKind, issue_type: str | None, settings: Settings
) -> list[Finding]:
    issues = settings.issues
    epic_type = issues.epic_type.lower()
    if kind is not TicketKind.REQUEST or (issue_type or "").lower() == epic_type:
        return []
    wrong = {phrase.lower() for phrase in issues.request_wrong_epic_phrases}
    seen: set[tuple[str, str]] = set()
    findings = []
    for link in iter_links(fields):
        if link.phrase.lower() in wrong and link.issue_type.lower() == epic_type:
            if (link.key, link.phrase.lower()) in seen:
                continue
            seen.add((link.key, link.phrase.lower()))
            correct = issues.request_parent_phrases[0] if issues.request_parent_phrases else ""
            findings.append(
                Finding(
                    FindingCode.REQUEST_WRONG_EPIC_LINK,
                    f"Linked to Epic {link.key} as '{link.phrase}'",
                    field="issue link",
                    related_key=link.key,
                    suggestion=f"Replace the link with '{correct}'",
                )
            )
    return findings


def sort_findings(findings: list[Finding]) -> tuple[Finding, ...]:
    return tuple(
        sorted(
            findings, key=lambda f: (f.code.value, f.field or "", f.related_key or "", f.message)
        )
    )
