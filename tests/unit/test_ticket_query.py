import dataclasses
from datetime import UTC, datetime

import pytest

from jira_dashboard.integrations.jira_client import TicketFailure
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
from jira_dashboard.services.ticket_query import (
    UNKNOWN_LABEL,
    TicketFilter,
    children_of,
    facets,
    filter_tickets,
    group,
    make_snapshot,
    natural_key,
    parent_of,
    sort_tickets,
    summarise,
)


def make(key: str, **kwargs) -> Ticket:
    defaults = {
        "jira_key": key,
        "summary": f"Summary of {key}",
        "project": Project("CAE", "VE_CAE"),
        "status": TicketStatus.NEW,
    }
    return Ticket(**(defaults | kwargs))


def user(name: str) -> User:
    return User(name, name.title())


def keys(tickets) -> list[str]:
    return [ticket.jira_key for ticket in tickets]


def test_empty_filter_returns_everything_in_natural_order() -> None:
    tickets = [make("CAE-100"), make("CAE-99"), make("CAE-1000")]
    assert keys(filter_tickets(tickets)) == ["CAE-99", "CAE-100", "CAE-1000"]


def test_natural_order_other_prefixes_and_unparsable_last() -> None:
    tickets = [make("ZZ-1"), make("not a key"), make("CAE-2"), make("CAE-10")]
    assert keys(sort_tickets(tickets)) == ["CAE-2", "CAE-10", "ZZ-1", "not a key"]
    assert natural_key("CAE-99") < natural_key("CAE-100")


def test_combined_criteria() -> None:
    tickets = [
        make("CAE-1", domain=Domain.STATIC, status=TicketStatus.IN_PROGRESS),
        make("CAE-2", domain=Domain.DYNAMIC, status=TicketStatus.IN_PROGRESS),
        make("CAE-3", domain=Domain.THERMAL, status=TicketStatus.IN_PROGRESS),
        make("CAE-4", domain=Domain.STATIC, status=TicketStatus.NEW),
    ]
    criteria = TicketFilter(
        domains=frozenset({Domain.STATIC, Domain.DYNAMIC}),
        statuses=frozenset({TicketStatus.IN_PROGRESS}),
    )
    assert keys(filter_tickets(tickets, criteria)) == ["CAE-1", "CAE-2"]


def test_unknown_values_are_selectable() -> None:
    tickets = [
        make("CAE-1", assignee=user("ann")),
        make("CAE-2"),
        make("CAE-3", domain=Domain.UNSPECIFIED),
        make("CAE-4", sprint=Sprint(1, "Sprint A", "ACTIVE"), priority="Major"),
    ]
    assert keys(filter_tickets(tickets, TicketFilter(assignees=frozenset({None})))) == [
        "CAE-2",
        "CAE-3",
        "CAE-4",
    ]
    assert keys(filter_tickets(tickets, TicketFilter(assignees=frozenset({"ann", None})))) == [
        "CAE-1",
        "CAE-2",
        "CAE-3",
        "CAE-4",
    ]
    assert keys(filter_tickets(tickets, TicketFilter(sprints=frozenset({"Sprint A"})))) == ["CAE-4"]
    assert keys(filter_tickets(tickets, TicketFilter(priorities=frozenset({None})))) == [
        "CAE-1",
        "CAE-2",
        "CAE-3",
    ]
    assert "CAE-3" in keys(filter_tickets(tickets, TicketFilter(domains=frozenset({None}))))


def test_project_and_kind_filters() -> None:
    other = make("SPDMT-5", project=Project("SPDMT", "S"), kind=TicketKind.TASK)
    tickets = [make("CAE-1", kind=TicketKind.REQUEST), other]
    assert keys(filter_tickets(tickets, TicketFilter(projects=frozenset({"SPDMT"})))) == ["SPDMT-5"]
    assert keys(filter_tickets(tickets, TicketFilter(kinds=frozenset({TicketKind.REQUEST})))) == [
        "CAE-1"
    ]


def test_text_search_matches_key_summary_assignee_and_requester() -> None:
    tickets = [
        make("CAE-1558", summary="Wand robustness"),
        make("CAE-2", summary="Handle drop test"),
        make("CAE-3", assignee=user("cchong")),
        make("CAE-4", requester="Mohamad Faizal"),
    ]

    def search(text):
        return keys(filter_tickets(tickets, TicketFilter(text=text)))

    assert search("1558") == ["CAE-1558"]
    assert search("DROP") == ["CAE-2"]
    assert search("cchong") == ["CAE-3"]
    assert search("faizal") == ["CAE-4"]
    assert search("  ") == ["CAE-2", "CAE-3", "CAE-4", "CAE-1558"]


def test_findings_only() -> None:
    finding = Finding(FindingCode.TASK_WITHOUT_PARENT, "No parent")
    tickets = [make("CAE-1"), make("CAE-2", findings=(finding,))]
    assert keys(filter_tickets(tickets, TicketFilter(only_with_findings=True))) == ["CAE-2"]


def test_assignee_facet_counts_and_unknown_last() -> None:
    tickets = [
        *(make(f"CAE-{n}", assignee=user("ann")) for n in range(1, 4)),
        make("CAE-4", assignee=user("bob")),
        make("CAE-5"),
        make("CAE-6"),
    ]
    values = facets(tickets)["assignee"]
    assert [(v.label, v.count) for v in values] == [
        ("Ann", 3),
        ("Bob", 1),
        (UNKNOWN_LABEL, 2),
    ]
    assert [v.value for v in values] == ["ann", "bob", None]


def test_ticket_in_several_dyson_projects_matches_any_of_them() -> None:
    tickets = [
        make("CAE-1", dyson_projects=("898B", "915")),
        make("CAE-2", dyson_projects=("915",)),
        make("CAE-3", dyson_projects=("1000",)),
        make("CAE-4"),
    ]
    assert keys(filter_tickets(tickets, TicketFilter(dyson_projects=frozenset({"915"})))) == [
        "CAE-1",
        "CAE-2",
    ]
    either = TicketFilter(dyson_projects=frozenset({"898B", "1000"}))
    assert keys(filter_tickets(tickets, either)) == ["CAE-1", "CAE-3"]


def test_unknown_dyson_project_is_selectable() -> None:
    tickets = [make("CAE-1", dyson_projects=("915",)), make("CAE-2")]
    unknown = TicketFilter(dyson_projects=frozenset({None}))
    assert keys(filter_tickets(tickets, unknown)) == ["CAE-2"]
    mixed = TicketFilter(dyson_projects=frozenset({None, "915"}))
    assert keys(filter_tickets(tickets, mixed)) == ["CAE-1", "CAE-2"]


def test_dyson_project_combines_with_other_criteria() -> None:
    tickets = [
        make("CAE-1", dyson_projects=("898B",), status=TicketStatus.IN_PROGRESS),
        make("CAE-2", dyson_projects=("898B",)),
        make("CAE-3", dyson_projects=("915",), status=TicketStatus.IN_PROGRESS),
    ]
    criteria = TicketFilter(
        dyson_projects=frozenset({"898B"}), statuses=frozenset({TicketStatus.IN_PROGRESS})
    )
    assert keys(filter_tickets(tickets, criteria)) == ["CAE-1"]


def test_dyson_project_facet_counts_each_project_and_orders_naturally() -> None:
    tickets = [
        make("CAE-1", dyson_projects=("898B", "915")),
        make("CAE-2", dyson_projects=("915",)),
        make("CAE-3", dyson_projects=("1000", "Transformation & Improvement")),
        make("CAE-4", dyson_projects=("unknown",)),
        make("CAE-5"),
    ]
    values = facets(tickets)["dyson_project"]
    assert [(v.label, v.count) for v in values] == [
        ("898B", 1),
        ("915", 2),
        ("1000", 1),
        ("Transformation & Improvement", 1),
        ("unknown", 1),
        (UNKNOWN_LABEL, 1),
    ]
    assert values[-1].value is None and values[-2].value == "unknown"


def test_dyson_project_facet_has_no_unknown_entry_when_all_have_projects() -> None:
    values = facets([make("CAE-1", dyson_projects=("915",))])["dyson_project"]
    assert [v.label for v in values] == ["915"]


def test_other_facets() -> None:
    tickets = [
        make("CAE-1", sprint=Sprint(1, "Sprint B", "ACTIVE"), domain=Domain.STATIC),
        make("CAE-2", sprint=Sprint(2, "Sprint A", "FUTURE"), domain=Domain.UNSPECIFIED),
        make("CAE-3", status=TicketStatus.UNKNOWN, raw_status="Implemented"),
    ]
    result = facets(tickets)
    assert [v.label for v in result["sprint"]] == ["Sprint A", "Sprint B", UNKNOWN_LABEL]
    assert [v.label for v in result["domain"]] == ["Static", UNKNOWN_LABEL]
    statuses = {v.value: v.label for v in result["status"]}
    assert statuses[TicketStatus.UNKNOWN] == "Unknown (Implemented)"
    assert statuses[TicketStatus.NEW] == "New"
    assert {v.label for v in result["kind"]} == {"Other"}


def test_snapshot_lookup_in_both_groups_and_immutable() -> None:
    snapshot = make_snapshot([make("CAE-2")], [make("CAE-1"), make("CAE-2")])
    assert snapshot.get("CAE-1").jira_key == "CAE-1"
    assert snapshot.get("CAE-2") in snapshot.tickets
    assert keys(snapshot.context) == ["CAE-1"]
    assert snapshot.get("CAE-9") is None and snapshot.get(None) is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.tickets = ()
    with pytest.raises(TypeError):
        snapshot.index["CAE-5"] = make("CAE-5")


def hierarchy():
    epic = make("CAE-1513", kind=TicketKind.REQUEST, issue_type="Epic")
    risk = make("CAE-1558", kind=TicketKind.REQUEST, parent_key="CAE-1513")
    task = make("CAE-1628", kind=TicketKind.TASK, parent_key="CAE-1558")
    return epic, risk, task


def test_parent_and_children_lookup() -> None:
    epic, risk, task = hierarchy()
    snapshot = make_snapshot([risk, task], [epic])
    assert parent_of(snapshot, task).jira_key == "CAE-1558"
    assert parent_of(snapshot, epic) is None
    assert keys(children_of(snapshot, "CAE-1558")) == ["CAE-1628"]
    assert keys(children_of(snapshot, "CAE-1513")) == ["CAE-1558"]


def test_task_under_risk_under_epic() -> None:
    epic, risk, task = hierarchy()
    snapshot = make_snapshot([risk, task], [epic])
    view = group(snapshot.tickets, snapshot)
    assert [n.ticket.jira_key for n in view.roots] == ["CAE-1513"]
    (risk_node,) = view.roots[0].children
    assert risk_node.ticket.jira_key == "CAE-1558" and risk_node.matched
    assert [n.ticket.jira_key for n in risk_node.children] == ["CAE-1628"]
    assert view.roots[0].matched is False
    assert view.orphans == []


def test_filtered_out_parent_is_shown_unmatched() -> None:
    epic, risk, task = hierarchy()
    snapshot = make_snapshot([risk, task], [epic])
    view = group([task], snapshot)
    assert [n.ticket.jira_key for n in view.roots] == ["CAE-1513"]
    risk_node = view.roots[0].children[0]
    assert risk_node.matched is False
    assert risk_node.children[0].matched is True


def test_orphan_tasks_and_missing_parents() -> None:
    orphan = make("CAE-5", kind=TicketKind.TASK)
    lost = make("CAE-6", kind=TicketKind.TASK, parent_key="CAE-404")
    request = make("CAE-7", kind=TicketKind.REQUEST)
    snapshot = make_snapshot([orphan, lost, request])
    view = group(snapshot.tickets, snapshot)
    assert keys(view.orphans) == ["CAE-5"]
    assert [n.ticket.jira_key for n in view.roots] == ["CAE-6", "CAE-7"]


def test_parent_cycles_are_cut() -> None:
    a = make("CAE-1", parent_key="CAE-2", kind=TicketKind.REQUEST)
    b = make("CAE-2", parent_key="CAE-1", kind=TicketKind.REQUEST)
    snapshot = make_snapshot([a, b])
    view = group(snapshot.tickets, snapshot)
    assert len(view.roots) == 1
    assert len(view.roots[0].children) == 1


def test_summary_counts() -> None:
    finding = Finding(FindingCode.TASK_WITHOUT_PARENT, "No parent")
    tickets = [
        make("CAE-1", kind=TicketKind.TASK, issue_type="Task", findings=(finding,)),
        make("CAE-2", kind=TicketKind.TASK, issue_type="Task"),
        make("CAE-3", kind=TicketKind.TASK, issue_type="Task"),
        make("CAE-4", kind=TicketKind.REQUEST, issue_type="Risk"),
        make("CAE-5", kind=TicketKind.REQUEST, issue_type="Risk"),
    ]
    when = datetime(2026, 11, 13, tzinfo=UTC)
    snapshot = make_snapshot(tickets, failures=[TicketFailure("CAE-9", "bad")], refreshed_at=when)
    summary = summarise(snapshot)
    assert summary.total == 5
    assert summary.by_issue_type == {"Task": 3, "Risk": 2}
    assert summary.by_kind == {"TASK": 3, "REQUEST": 2}
    assert summary.by_status == {"NEW": 5}
    assert summary.with_findings == 1
    assert summary.findings_by_code == {"TASK_WITHOUT_PARENT": 1}
    assert summary.unreadable == 1 and summary.refreshed_at == when
