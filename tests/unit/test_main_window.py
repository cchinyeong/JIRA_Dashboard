import re
import threading
from datetime import UTC, datetime

import pytest
from PySide6.QtCore import QModelIndex, Qt
from ticket_factory import make_ticket

from jira_dashboard.models import Finding, FindingCode
from jira_dashboard.services.ticket_query import (
    facets,
    filter_tickets,
    group,
    make_snapshot,
    summarise,
)
from jira_dashboard.services.ticket_service import RefreshResult
from jira_dashboard.ui.main_window import NOT_CONFIGURED_URL, MainWindow
from jira_dashboard.ui.refresh_worker import RefreshWorker

OK = RefreshResult("ok", ticket_count=2)
LINK_BASE = "https://jira.example.test/browse/"


class FakeService:
    def __init__(self, tickets=(), results=None, gate: threading.Event | None = None) -> None:
        self.tickets = list(tickets)
        self.context: list = []
        self.results = list(results or [OK])
        self.gate = gate
        self.refresh_threads: list[threading.Thread] = []
        self.refreshed_at = datetime(2026, 11, 13, 7, 30, tzinfo=UTC)

    def refresh(self) -> RefreshResult:
        self.refresh_threads.append(threading.current_thread())
        if self.gate is not None:
            assert self.gate.wait(5)
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]

    def list_tickets(self, criteria=None):
        return filter_tickets(self.tickets, criteria)

    def facets(self):
        return facets(self.tickets)

    def grouped(self, tickets=None):
        snapshot = self.snapshot
        return group(snapshot.tickets if tickets is None else tickets, snapshot)

    @property
    def snapshot(self):
        return make_snapshot(self.tickets, self.context, refreshed_at=self.refreshed_at)

    def summary(self):
        return summarise(self.snapshot)

    def ticket_link(self, ticket):
        return None if ticket.jira_key == "CAE-NOLINK" else LINK_BASE + ticket.jira_key


def make_window(qtbot, service, **kwargs) -> MainWindow:
    window = MainWindow(service, **kwargs)
    qtbot.addWidget(window)
    window.show()
    return window


def refresh(qtbot, window: MainWindow) -> None:
    window.start_refresh()
    qtbot.waitUntil(lambda: window.refresh_action.isEnabled(), timeout=5000)


def row_keys(window: MainWindow) -> list[str]:
    proxy = window.table.model()
    return [proxy.index(r, 0).data() for r in range(proxy.rowCount(QModelIndex()))]


def test_worker_runs_off_the_interface_thread_and_delivers_result(qtbot) -> None:
    service = FakeService()
    worker = RefreshWorker(service)
    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(worker)
    assert blocker.args == [OK]
    assert service.refresh_threads[0] is not threading.main_thread()


def test_worker_reports_unexpected_exception_as_failed(qtbot) -> None:
    class Broken(FakeService):
        def refresh(self):
            raise RuntimeError("boom")

    worker = RefreshWorker(Broken())
    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        worker.run()
    assert blocker.args[0].status == "failed"
    assert blocker.args[0].error_kind == "unexpected"


def test_refresh_disables_button_while_running_then_shows_data(qtbot) -> None:
    gate = threading.Event()
    service = FakeService([make_ticket("CAE-2"), make_ticket("CAE-1")], gate=gate)
    window = make_window(qtbot, service)
    window.start_refresh()
    assert not window.refresh_action.isEnabled()
    assert window.progress.isVisibleTo(window)
    assert row_keys(window) == []
    gate.set()
    qtbot.waitUntil(lambda: window.refresh_action.isEnabled(), timeout=5000)
    assert not window.progress.isVisibleTo(window)
    assert row_keys(window) == ["CAE-1", "CAE-2"]


def test_failed_refresh_keeps_rows_and_shows_message(qtbot) -> None:
    failed = RefreshResult("failed", error_kind="timeout", message="Jira did not respond.")
    service = FakeService([make_ticket("CAE-1")], results=[OK, failed, OK])
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    refresh(qtbot, window)
    assert row_keys(window) == ["CAE-1"]
    assert window.banner.isVisibleTo(window)
    assert "Jira did not respond." in window.banner_label.text()
    refresh(qtbot, window)
    assert not window.banner.isVisibleTo(window)


def test_warning_is_shown(qtbot) -> None:
    warned = RefreshResult("ok", warnings=("Parent tickets could not be loaded: timeout",))
    window = make_window(qtbot, FakeService([make_ticket()], results=[warned]))
    refresh(qtbot, window)
    assert "Parent tickets could not be loaded" in window.banner_label.text()


def test_status_bar_shows_counts_and_time(qtbot) -> None:
    finding = Finding(FindingCode.TASK_WITHOUT_PARENT, "No parent.")
    tickets = [make_ticket("CAE-1", findings=(finding,)), make_ticket("CAE-2")]
    window = make_window(qtbot, FakeService(tickets))
    refresh(qtbot, window)
    text = window.summary_label.text()
    assert "2 tickets" in text
    assert "1 with findings" in text
    assert "0 unreadable" in text
    assert re.search(r"refreshed \d\d:\d\d", text)


def test_placeholder_address_shows_message_and_disables_refresh(qtbot) -> None:
    service = FakeService()
    window = make_window(qtbot, service, not_configured=NOT_CONFIGURED_URL)
    assert "jira.base_url" in window.message_label.text()
    assert window.stack.currentWidget() is window.message_page
    assert not window.refresh_action.isEnabled()
    window.start_refresh()
    assert service.refresh_threads == []


def test_no_token_shows_instructions_and_keeps_refresh_available(qtbot) -> None:
    result = RefreshResult(
        "failed", error_kind="no_token", message="Secret 'jira-pat' is not stored."
    )
    window = make_window(qtbot, FakeService(results=[result]))
    refresh(qtbot, window)
    assert "Secret 'jira-pat' is not stored." in window.message_label.text()
    assert "docs/security.md" in window.message_label.text()
    assert window.stack.currentWidget() is window.message_page
    assert row_keys(window) == []


def select_first(window: MainWindow) -> None:
    window.table.selectRow(0)


def test_open_in_jira_opens_allowed_link(qtbot) -> None:
    opened: list[str] = []
    window = make_window(qtbot, FakeService([make_ticket("CAE-1")]), opener=opened.append)
    refresh(qtbot, window)
    assert not window.open_action.isEnabled()
    select_first(window)
    assert window.open_action.isEnabled()
    window.open_action.trigger()
    window._on_double_clicked(window.table.model().index(0, 0))
    assert opened == [LINK_BASE + "CAE-1"] * 2


def test_refused_link_opens_nothing_and_disables_action(qtbot) -> None:
    opened: list[str] = []
    window = make_window(qtbot, FakeService([make_ticket("CAE-NOLINK")]), opener=opened.append)
    refresh(qtbot, window)
    select_first(window)
    assert not window.open_action.isEnabled()
    window.open_selected()
    window._on_double_clicked(window.table.model().index(0, 0))
    assert opened == []


@pytest.mark.parametrize("column", [0, 3])
def test_table_is_read_only(qtbot, column) -> None:
    window = make_window(qtbot, FakeService([make_ticket("CAE-1")]))
    refresh(qtbot, window)
    index = window.table.model().index(0, column)
    assert not window.table.model().flags(index) & Qt.ItemFlag.ItemIsEditable


def test_selecting_a_row_fills_the_details_panel(qtbot) -> None:
    window = make_window(qtbot, FakeService([make_ticket("CAE-1", summary="First")]))
    refresh(qtbot, window)
    assert window.details.hint.isVisibleTo(window)
    select_first(window)
    assert window.details.title.text() == "CAE-1  First"
    window.table.clearSelection()
    assert window.details.hint.isVisibleTo(window)


def test_details_panel_shows_loaded_parent(qtbot) -> None:
    service = FakeService([make_ticket("CAE-2", parent_key="CAE-1")])
    service.context = [make_ticket("CAE-1", summary="Epic summary", issue_type="Epic")]
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    select_first(window)
    assert window.details.value("Parent") == "CAE-1 · Epic · Epic summary"


def test_details_button_opens_the_allowed_link(qtbot) -> None:
    opened: list[str] = []
    window = make_window(qtbot, FakeService([make_ticket("CAE-1")]), opener=opened.append)
    refresh(qtbot, window)
    select_first(window)
    assert window.details.open_button.isEnabled()
    window.details.open_button.click()
    assert opened == [LINK_BASE + "CAE-1"]


def test_selection_kept_across_refresh_with_new_values(qtbot) -> None:
    service = FakeService([make_ticket("CAE-1", priority="High")], results=[OK, OK])
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    select_first(window)
    service.tickets = [make_ticket("CAE-0"), make_ticket("CAE-1", priority="Low")]
    refresh(qtbot, window)
    assert window._selected_ticket().jira_key == "CAE-1"
    assert window.details.value("Priority") == "Low"


def test_selection_cleared_when_ticket_disappears(qtbot) -> None:
    service = FakeService([make_ticket("CAE-1")], results=[OK, OK])
    window = make_window(qtbot, service)
    refresh(qtbot, window)
    select_first(window)
    service.tickets = [make_ticket("CAE-2")]
    refresh(qtbot, window)
    assert window._selected_ticket() is None
    assert window.details.hint.isVisibleTo(window)
