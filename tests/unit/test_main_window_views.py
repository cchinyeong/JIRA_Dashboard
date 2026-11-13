from test_main_window import LINK_BASE, OK, FakeService, make_window, refresh, row_keys
from ticket_factory import make_ticket

from jira_dashboard.models import TicketKind, TicketStatus
from jira_dashboard.ui.hierarchy_model import ORPHANS_TITLE
from jira_dashboard.ui.main_window import NO_MATCH
from jira_dashboard.ui.ticket_model import TICKET_ROLE


def epic(key: str, **kw):
    return make_ticket(key, kind=TicketKind.REQUEST, issue_type="Epic", **kw)


def task(key: str, parent: str | None = None, **kw):
    return make_ticket(key, kind=TicketKind.TASK, parent_key=parent, **kw)


def sample() -> list:
    return [
        epic("CAE-1"),
        task("CAE-2", "CAE-1", status=TicketStatus.NEW),
        task("CAE-3", "CAE-1"),
        task("CAE-4"),
    ]


def tree_top(window) -> list[str]:
    model = window._hierarchy
    return [model.item(r, 0).text() for r in range(model.rowCount())]


def select_in_tree(window, key: str) -> None:
    from PySide6.QtCore import QItemSelectionModel

    index = window._hierarchy.index_for_key(key)
    window.tree.selectionModel().select(
        index,
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )


def test_filter_bar_appears_only_with_data(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    assert not window.filter_bar.isVisibleTo(window)
    refresh(qtbot, window)
    assert window.filter_bar.isVisibleTo(window)


def test_filter_narrows_the_table_and_the_status_bar(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    refresh(qtbot, window)
    assert "4 tickets" in window.summary_label.text()
    window.filter_bar.buttons["status"].set_checked(TicketStatus.NEW)
    assert row_keys(window) == ["CAE-2"]
    assert "1 of 4 tickets" in window.summary_label.text()
    window.filter_bar.clear()
    assert len(row_keys(window)) == 4
    assert "4 tickets" in window.summary_label.text()
    assert " of " not in window.summary_label.text()


def test_hierarchy_view_uses_the_same_filter(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    refresh(qtbot, window)
    window.filter_bar.hierarchy_button.setChecked(True)
    assert window.views.currentWidget() is window.tree
    assert tree_top(window) == ["CAE-1  Summary", f"{ORPHANS_TITLE} (1)"]
    window.filter_bar.buttons["status"].set_checked(TicketStatus.NEW)
    assert tree_top(window) == ["CAE-1  Summary"]
    parent_item = window._hierarchy.item(0, 0)
    assert parent_item.font().italic()
    assert parent_item.rowCount() == 1


def test_dyson_project_filter_narrows_the_table(qtbot) -> None:
    data = [
        make_ticket("CAE-1", dyson_projects=("898B", "915")),
        make_ticket("CAE-2", dyson_projects=("915",)),
        make_ticket("CAE-3", dyson_projects=("1000",)),
    ]
    window = make_window(qtbot, FakeService(data))
    refresh(qtbot, window)
    window.filter_bar.buttons["dyson_project"].set_checked("898B")
    assert row_keys(window) == ["CAE-1"]
    assert "1 of 3 tickets" in window.summary_label.text()
    window.filter_bar.buttons["dyson_project"].set_checked("915")
    assert row_keys(window) == ["CAE-1", "CAE-2"]


def test_filter_survives_refresh(qtbot) -> None:
    service = FakeService(sample(), results=[OK, OK])
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    window.filter_bar.buttons["status"].set_checked(TicketStatus.NEW)
    service.tickets = [*sample(), task("CAE-5", "CAE-1", status=TicketStatus.NEW)]
    refresh(qtbot, window)
    assert row_keys(window) == ["CAE-2", "CAE-5"]


def test_tree_selection_fills_panel_and_opens_link(qtbot) -> None:
    opened: list[str] = []
    window = make_window(qtbot, FakeService(sample()), opener=opened.append)
    refresh(qtbot, window)
    window.filter_bar.hierarchy_button.setChecked(True)
    select_in_tree(window, "CAE-3")
    assert window.details.title.text() == "CAE-3  Summary"
    assert window.details.value("Parent").startswith("CAE-1")
    window.open_action.trigger()
    window._on_double_clicked(window._hierarchy.index_for_key("CAE-3"))
    assert opened == [LINK_BASE + "CAE-3"] * 2


def test_group_node_is_not_a_ticket(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    refresh(qtbot, window)
    window.filter_bar.hierarchy_button.setChecked(True)
    group_index = window._hierarchy.index(1, 0)
    assert group_index.data(TICKET_ROLE) is None
    window.tree.setCurrentIndex(group_index)
    assert window._selected_ticket() is None
    assert window.details.hint.isVisibleTo(window)
    assert not window.open_action.isEnabled()


def test_selection_and_view_survive_refresh_in_the_tree(qtbot) -> None:
    service = FakeService(sample(), results=[OK, OK])
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    window.filter_bar.hierarchy_button.setChecked(True)
    select_in_tree(window, "CAE-3")
    service.tickets = [make_ticket("CAE-0"), *sample()]
    refresh(qtbot, window)
    assert window.views.currentWidget() is window.tree
    assert window._selected_ticket().jira_key == "CAE-3"


def test_selection_moves_between_views(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    refresh(qtbot, window)
    window.table.selectRow(1)
    key = window._selected_ticket().jira_key
    window.filter_bar.hierarchy_button.setChecked(True)
    assert window._selected_ticket().jira_key == key


def test_no_match_message_and_clear(qtbot) -> None:
    window = make_window(qtbot, FakeService(sample()))
    refresh(qtbot, window)
    window.filter_bar.search.setText("no such text")
    qtbot.waitUntil(lambda: window.stack.currentWidget() is window.message_page, timeout=2000)
    assert window.message_label.text() == NO_MATCH
    assert window.filter_bar.isVisibleTo(window)
    window.filter_bar.clear_button.click()
    assert window.stack.currentWidget() is window.splitter
    assert len(row_keys(window)) == 4
