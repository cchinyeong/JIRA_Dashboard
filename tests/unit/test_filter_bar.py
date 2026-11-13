from ticket_factory import make_ticket

from jira_dashboard.models import Domain, Sprint, TicketKind, TicketStatus, User
from jira_dashboard.services.ticket_query import TicketFilter, facets, filter_tickets
from jira_dashboard.ui.filter_bar import FilterBar


def tickets():
    ann = User(username="ann", display_name="Ann")
    bob = User(username="bob", display_name="Bob")
    return [
        make_ticket("CAE-1", assignee=ann, domain=Domain.CFD, kind=TicketKind.TASK),
        make_ticket("CAE-2", assignee=bob, domain=Domain.CFD, status=TicketStatus.NEW),
        make_ticket("CAE-3", assignee=None, domain=Domain.STATIC, sprint=None),
        make_ticket("CAE-4", status=TicketStatus.UNKNOWN, raw_status="Implemented"),
    ]


def make_bar(qtbot, data=None) -> tuple[FilterBar, list[TicketFilter]]:
    bar = FilterBar(debounce_ms=10)
    qtbot.addWidget(bar)
    emitted: list[TicketFilter] = []
    bar.changed.connect(emitted.append)
    bar.set_facets(facets(data or tickets()))
    return bar, emitted


def keys(criteria: TicketFilter, data=None) -> list[str]:
    return [t.jira_key for t in filter_tickets(data or tickets(), criteria)]


def test_combined_filters(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.buttons["status"].set_checked(TicketStatus.IN_PROGRESS)
    bar.buttons["domain"].set_checked(Domain.CFD)
    assert keys(emitted[-1]) == ["CAE-1"]


def test_several_values_of_one_filter(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.buttons["assignee"].set_checked("ann")
    bar.buttons["assignee"].set_checked("bob")
    assert keys(emitted[-1]) == ["CAE-1", "CAE-2", "CAE-4"]
    assert bar.buttons["assignee"].text() == "Assignee (2)"


def test_text_search_after_debounce(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.search.setText("cae-3")
    assert emitted == []
    qtbot.waitUntil(lambda: len(emitted) == 1, timeout=2000)
    assert keys(emitted[0]) == ["CAE-3"]


def test_only_with_findings_switch(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.findings_only.setChecked(True)
    assert emitted[-1].only_with_findings is True


def test_clear_returns_to_neutral_and_emits_once(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.buttons["status"].set_checked(TicketStatus.NEW)
    bar.findings_only.setChecked(True)
    bar.search.setText("x")
    count = len(emitted)
    bar.clear()
    assert len(emitted) == count + 1
    assert emitted[-1] == TicketFilter()
    assert not bar.is_active()
    assert bar.search.text() == ""
    assert bar.buttons["status"].text() == "Status"


def test_menu_entries_have_counts_and_unknown_last(qtbot) -> None:
    bar, _ = make_bar(qtbot)
    assignee_entries = bar.buttons["assignee"].entries()
    assert assignee_entries[-1].startswith("Unknown")
    assert "Ann (2)" in assignee_entries
    status_entries = bar.buttons["status"].entries()
    assert "In Progress (2)" in status_entries
    assert any(entry.startswith("Unknown (Implemented)") for entry in status_entries)
    assert not any(entry.startswith("Closed") for entry in status_entries)


def test_selection_kept_when_values_still_exist(qtbot) -> None:
    bar, emitted = make_bar(qtbot)
    bar.buttons["status"].set_checked(TicketStatus.NEW)
    count = len(emitted)
    bar.set_facets(facets(tickets()))
    assert bar.buttons["status"].selected() == frozenset({TicketStatus.NEW})
    assert len(emitted) == count


def test_vanished_value_is_dropped_and_filter_updated(qtbot) -> None:
    data = tickets() + [make_ticket("CAE-5", sprint=Sprint(2, "Sprint 9", "ACTIVE"))]
    bar, emitted = make_bar(qtbot, data)
    bar.buttons["sprint"].set_checked("Sprint 9")
    bar.buttons["status"].set_checked(TicketStatus.NEW)
    bar.set_facets(facets(tickets()))
    assert bar.buttons["sprint"].selected() == frozenset()
    assert bar.buttons["status"].selected() == frozenset({TicketStatus.NEW})
    assert emitted[-1].sprints == frozenset()
    assert emitted[-1].statuses == frozenset({TicketStatus.NEW})


def project_tickets():
    return [
        make_ticket("CAE-1", dyson_projects=("898B", "915"), status=TicketStatus.IN_PROGRESS),
        make_ticket("CAE-2", dyson_projects=("915",), status=TicketStatus.NEW),
        make_ticket("CAE-3", dyson_projects=("1000",), status=TicketStatus.IN_PROGRESS),
        make_ticket("CAE-4", status=TicketStatus.IN_PROGRESS),
    ]


def test_dyson_project_menu_has_counts_natural_order_and_unknown_last(qtbot) -> None:
    bar, _ = make_bar(qtbot, project_tickets())
    assert bar.buttons["dyson_project"].entries() == [
        "898B (1)",
        "915 (2)",
        "1000 (1)",
        "Unknown (1)",
    ]
    assert bar.buttons["dyson_project"].text() == "Dyson Project"


def test_dyson_project_selection_matches_any_and_combines(qtbot) -> None:
    data = project_tickets()
    bar, emitted = make_bar(qtbot, data)
    bar.buttons["dyson_project"].set_checked("915")
    assert keys(emitted[-1], data) == ["CAE-1", "CAE-2"]
    bar.buttons["status"].set_checked(TicketStatus.IN_PROGRESS)
    assert keys(emitted[-1], data) == ["CAE-1"]
    assert emitted[-1].dyson_projects == frozenset({"915"})
    assert bar.buttons["dyson_project"].text() == "Dyson Project (1)"


def test_view_switch_emits(qtbot) -> None:
    bar, _ = make_bar(qtbot)
    views: list[str] = []
    bar.view_changed.connect(views.append)
    bar.hierarchy_button.setChecked(True)
    assert bar.view == "hierarchy" and views == ["hierarchy"]
    bar.table_button.setChecked(True)
    assert views == ["hierarchy", "table"]
