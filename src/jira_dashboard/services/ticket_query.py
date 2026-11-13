import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from jira_dashboard.integrations.jira_client import TicketFailure
from jira_dashboard.models import Domain, Ticket, TicketKind, TicketStatus

UNKNOWN_LABEL = "Unknown"
_KEY = re.compile(r"^(?P<prefix>[A-Za-z][A-Za-z0-9_]*)-(?P<number>\d+)$")


def natural_key(key: str) -> tuple[int, str, int, str]:
    match = _KEY.match(key)
    if not match:
        return (1, key, 0, key)
    return (0, match["prefix"], int(match["number"]), key)


def sort_tickets(tickets: Iterable[Ticket]) -> list[Ticket]:
    return sorted(tickets, key=lambda ticket: natural_key(ticket.jira_key))


@dataclass(frozen=True, slots=True)
class Snapshot:
    tickets: tuple[Ticket, ...] = ()
    context: tuple[Ticket, ...] = ()
    failures: tuple[TicketFailure, ...] = ()
    warnings: tuple[str, ...] = ()
    refreshed_at: datetime | None = None
    index: Mapping[str, Ticket] = field(default_factory=dict, repr=False, compare=False)

    def get(self, key: str | None) -> Ticket | None:
        return self.index.get(key) if key else None


def make_snapshot(
    tickets: Iterable[Ticket],
    context: Iterable[Ticket] = (),
    failures: Iterable[TicketFailure] = (),
    warnings: Iterable[str] = (),
    refreshed_at: datetime | None = None,
) -> Snapshot:
    listed = tuple(sort_tickets(tickets))
    listed_keys = {ticket.jira_key for ticket in listed}
    extra = tuple(sort_tickets(t for t in context if t.jira_key not in listed_keys))
    index = {ticket.jira_key: ticket for ticket in (*extra, *listed)}
    return Snapshot(
        tickets=listed,
        context=extra,
        failures=tuple(failures),
        warnings=tuple(warnings),
        refreshed_at=refreshed_at,
        index=MappingProxyType(index),
    )


def _domain(ticket: Ticket) -> Domain | None:
    return None if ticket.domain is Domain.UNSPECIFIED else ticket.domain


EXTRACTORS: dict[str, Callable[[Ticket], object]] = {
    "project": lambda t: t.project.key,
    "dyson_project": lambda t: t.dyson_projects,
    "domain": _domain,
    "assignee": lambda t: t.assignee.username if t.assignee else None,
    "sprint": lambda t: t.sprint.name if t.sprint else None,
    "status": lambda t: t.status,
    "priority": lambda t: t.priority or None,
    "kind": lambda t: t.kind,
}


def _values(field_name: str, ticket: Ticket) -> tuple[object, ...]:
    """The ticket's values for a facet; a multi-valued field gives all, none gives unknown."""
    value = EXTRACTORS[field_name](ticket)
    if isinstance(value, tuple):
        return value or (None,)
    return (value,)


def _natural_text(text: str) -> list[tuple[int, int | str]]:
    """Orders numbers by value before names: 898B, 915, 1000, then Transformation."""
    parts = re.split(r"(\d+)", text)
    return [(0, int(p)) if p.isdigit() else (1, p.lower()) for p in parts if p]


NATURAL_FACETS = frozenset({"dyson_project"})


@dataclass(frozen=True, slots=True)
class TicketFilter:
    projects: frozenset = frozenset()
    dyson_projects: frozenset = frozenset()
    domains: frozenset = frozenset()
    assignees: frozenset = frozenset()
    sprints: frozenset = frozenset()
    statuses: frozenset = frozenset()
    priorities: frozenset = frozenset()
    kinds: frozenset = frozenset()
    text: str = ""
    only_with_findings: bool = False


_CRITERIA = (
    ("projects", "project"),
    ("dyson_projects", "dyson_project"),
    ("domains", "domain"),
    ("assignees", "assignee"),
    ("sprints", "sprint"),
    ("statuses", "status"),
    ("priorities", "priority"),
    ("kinds", "kind"),
)


def matches(ticket: Ticket, criteria: TicketFilter) -> bool:
    for attribute, field_name in _CRITERIA:
        allowed = getattr(criteria, attribute)
        if allowed and not allowed.intersection(_values(field_name, ticket)):
            return False
    needle = criteria.text.strip().lower()
    if needle:
        parts = [ticket.jira_key, ticket.summary, ticket.requester]
        if ticket.assignee:
            parts.append(ticket.assignee.display_name)
        if needle not in " ".join(part for part in parts if part).lower():
            return False
    return not (criteria.only_with_findings and not ticket.findings)


def filter_tickets(tickets: Iterable[Ticket], criteria: TicketFilter | None = None) -> list[Ticket]:
    criteria = criteria or TicketFilter()
    return sort_tickets(ticket for ticket in tickets if matches(ticket, criteria))


@dataclass(frozen=True, slots=True)
class FacetValue:
    value: object
    label: str
    count: int


def _label(field_name: str, ticket: Ticket, value: object) -> str:
    if value is None:
        return UNKNOWN_LABEL
    if field_name == "assignee":
        return ticket.assignee.display_name
    if field_name in ("domain", "kind", "status"):
        return value.value.replace("_", " ").title()
    return str(value)


def facets(tickets: Iterable[Ticket]) -> dict[str, list[FacetValue]]:
    tickets = list(tickets)
    result: dict[str, list[FacetValue]] = {}
    for field_name in EXTRACTORS:
        counts: Counter = Counter()
        labels: dict[object, str] = {}
        raw_unknown: set[str] = set()
        for ticket in tickets:
            for value in _values(field_name, ticket):
                counts[value] += 1
                labels.setdefault(value, _label(field_name, ticket, value))
                if field_name == "status" and value is TicketStatus.UNKNOWN and ticket.raw_status:
                    raw_unknown.add(ticket.raw_status)
        if TicketStatus.UNKNOWN in labels and raw_unknown:
            labels[TicketStatus.UNKNOWN] = f"Unknown ({', '.join(sorted(raw_unknown))})"
        values = [FacetValue(value, labels[value], count) for value, count in counts.items()]
        if field_name in NATURAL_FACETS:
            values.sort(key=lambda item: (item.value is None, _natural_text(item.label)))
        else:
            values.sort(key=lambda item: (item.value is None, item.label.lower()))
        result[field_name] = values
    return result


def parent_of(snapshot: Snapshot, ticket: Ticket) -> Ticket | None:
    return snapshot.get(ticket.parent_key)


def children_of(snapshot: Snapshot, key: str) -> list[Ticket]:
    everything = (*snapshot.tickets, *snapshot.context)
    return sort_tickets(ticket for ticket in everything if ticket.parent_key == key)


@dataclass(slots=True)
class TreeNode:
    ticket: Ticket
    matched: bool
    children: list[TreeNode] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GroupedView:
    roots: list[TreeNode]
    orphans: list[Ticket]


def _creates_cycle(child: str, parent: str, linked: dict[str, str]) -> bool:
    current: str | None = parent
    seen = set()
    while current is not None and current not in seen:
        if current == child:
            return True
        seen.add(current)
        current = linked.get(current)
    return False


def group(tickets: Sequence[Ticket], snapshot: Snapshot) -> GroupedView:
    listed = {ticket.jira_key for ticket in tickets}
    nodes: dict[str, TreeNode] = {}
    linked: dict[str, str] = {}
    orphans: list[Ticket] = []

    def node_for(ticket: Ticket) -> TreeNode:
        if ticket.jira_key not in nodes:
            nodes[ticket.jira_key] = TreeNode(ticket, ticket.jira_key in listed)
        return nodes[ticket.jira_key]

    for ticket in sort_tickets(tickets):
        if ticket.kind is TicketKind.TASK and not ticket.parent_key:
            orphans.append(ticket)
            continue
        current = ticket
        seen = {current.jira_key}
        while True:
            node = node_for(current)
            parent = parent_of(snapshot, current)
            if parent is None or parent.jira_key in seen:
                break
            parent_node = node_for(parent)
            if current.jira_key not in linked and not _creates_cycle(
                current.jira_key, parent.jira_key, linked
            ):
                linked[current.jira_key] = parent.jira_key
                parent_node.children.append(node)
            seen.add(parent.jira_key)
            current = parent

    for node in nodes.values():
        node.children.sort(key=lambda child: natural_key(child.ticket.jira_key))
    roots = [node for key, node in nodes.items() if key not in linked]
    roots.sort(key=lambda node: natural_key(node.ticket.jira_key))
    return GroupedView(roots=roots, orphans=orphans)


@dataclass(frozen=True, slots=True)
class Summary:
    total: int
    by_kind: dict[str, int]
    by_issue_type: dict[str, int]
    by_status: dict[str, int]
    with_findings: int
    findings_by_code: dict[str, int]
    unreadable: int
    refreshed_at: datetime | None


def summarise(snapshot: Snapshot) -> Summary:
    tickets = snapshot.tickets
    return Summary(
        total=len(tickets),
        by_kind=dict(Counter(t.kind.value for t in tickets)),
        by_issue_type=dict(Counter(t.issue_type or UNKNOWN_LABEL for t in tickets)),
        by_status=dict(Counter(t.status.value for t in tickets)),
        with_findings=sum(1 for t in tickets if t.findings),
        findings_by_code=dict(Counter(f.code.value for t in tickets for f in t.findings)),
        unreadable=len(snapshot.failures),
        refreshed_at=snapshot.refreshed_at,
    )
