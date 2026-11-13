import logging
from collections.abc import Callable

from PySide6.QtCore import QModelIndex, QPoint, Qt, QThreadPool, QUrl, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QStackedWidget,
    QTableView,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from jira_dashboard.models import Ticket
from jira_dashboard.services.ticket_service import RefreshResult, TicketService
from jira_dashboard.ui.refresh_worker import RefreshWorker
from jira_dashboard.ui.sort_proxy import TicketSortProxy
from jira_dashboard.ui.ticket_model import (
    KEY_COLUMN,
    TICKET_ROLE,
    TicketTableModel,
)

logger = logging.getLogger(__name__)

NOT_CONFIGURED_URL = (
    "Jira is not configured. Set jira.base_url in settings.local.toml (or the "
    "JIRA_DASHBOARD_JIRA__BASE_URL environment variable) and restart the application. "
    "See docs/security.md."
)
NO_TOKEN_HELP = "See docs/security.md for how to store the Jira token, then press Refresh."
SUMMARY_COLUMN = 1
MAX_SUMMARY_WIDTH = 420

_ERROR_STYLE = "background:#fde7e9; color:#7a1f24; padding:6px;"
_WARNING_STYLE = "background:#fff4ce; color:#5c4400; padding:6px;"


def open_in_browser(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: TicketService,
        *,
        opener: Callable[[str], object] = open_in_browser,
        not_configured: str | None = None,
        pool: QThreadPool | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._opener = opener
        self._pool = pool or QThreadPool.globalInstance()
        self._busy = False
        self._closed = False
        self._configured = not_configured is None
        self.setWindowTitle("VE Jira Operations Dashboard")
        self.resize(1400, 800)

        self._model = TicketTableModel(self)
        self._proxy = TicketSortProxy(self)
        self._proxy.setSourceModel(self._model)

        self._build_actions()
        self._build_central()
        self._build_status_bar()

        if not_configured is not None:
            self._show_message(not_configured)
        self._update_actions()

    def _build_actions(self) -> None:
        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.refresh_action.triggered.connect(self.start_refresh)
        self.open_action = QAction("Open in Jira", self)
        self.open_action.triggered.connect(self.open_selected)
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.open_action)
        self.addToolBar(toolbar)

    def _build_central(self) -> None:
        self.banner = QFrame()
        self.banner_label = QLabel()
        self.banner_label.setWordWrap(True)
        dismiss = QToolButton()
        dismiss.setText("×")
        dismiss.clicked.connect(self.banner.hide)
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.addWidget(self.banner_label, 1)
        banner_layout.addWidget(dismiss)
        self.banner.hide()

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(False)
        self.table.sortByColumn(KEY_COLUMN, Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().hide()
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.selectionModel().selectionChanged.connect(self._update_actions)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setMargin(40)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.message_label)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.banner)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def _build_status_bar(self) -> None:
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(140)
        self.progress.hide()
        self.summary_label = QLabel("No data yet")
        self.statusBar().addWidget(self.summary_label, 1)
        self.statusBar().addPermanentWidget(self.progress)

    def _selected_ticket(self) -> Ticket | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].data(TICKET_ROLE)

    def _link_for(self, ticket: Ticket | None) -> str | None:
        return self._service.ticket_link(ticket) if ticket is not None else None

    def _update_actions(self, *_args) -> None:
        self.refresh_action.setEnabled(self._configured and not self._busy)
        self.open_action.setEnabled(self._link_for(self._selected_ticket()) is not None)

    def _show_message(self, text: str) -> None:
        self.message_label.setText(text)
        self.stack.setCurrentWidget(self.message_label)

    def _show_banner(self, text: str, style: str) -> None:
        self.banner_label.setText(text)
        self.banner.setStyleSheet(style)
        self.banner.show()

    def start_refresh(self) -> None:
        if self._busy or not self._configured:
            return
        self._busy = True
        self.progress.show()
        self._update_actions()
        worker = RefreshWorker(self._service)
        worker.signals.finished.connect(self._on_refresh_finished)
        self._pool.start(worker)

    @Slot(object)
    def _on_refresh_finished(self, result: RefreshResult) -> None:
        if self._closed:
            return
        self._busy = False
        self.progress.hide()
        if result.ok:
            self._apply_success(result)
        elif result.error_kind == "no_token":
            self._show_message(f"{result.message}\n\n{NO_TOKEN_HELP}")
            self.banner.hide()
        elif result.status == "failed":
            suffix = " Showing the previous data." if self._model.rowCount() else ""
            self._show_banner(f"Refresh failed: {result.message}{suffix}", _ERROR_STYLE)
        self._update_actions()

    def _apply_success(self, result: RefreshResult) -> None:
        self._model.set_tickets(self._service.list_tickets())
        self.stack.setCurrentWidget(self.table)
        self.table.resizeColumnsToContents()
        if self.table.columnWidth(SUMMARY_COLUMN) > MAX_SUMMARY_WIDTH:
            self.table.setColumnWidth(SUMMARY_COLUMN, MAX_SUMMARY_WIDTH)
        if result.warnings:
            self._show_banner("\n".join(result.warnings), _WARNING_STYLE)
        else:
            self.banner.hide()
        summary = self._service.summary()
        parts = [f"{summary.total} tickets"]
        if summary.refreshed_at is not None:
            parts.append(f"refreshed {summary.refreshed_at.astimezone():%H:%M}")
        parts.append(f"{summary.unreadable} unreadable")
        parts.append(f"{summary.with_findings} with findings")
        self.summary_label.setText(" · ".join(parts))

    def open_selected(self) -> None:
        link = self._link_for(self._selected_ticket())
        if link is not None:
            self._opener(link)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        link = self._link_for(index.data(TICKET_ROLE))
        if link is not None:
            self._opener(link)

    def _show_context_menu(self, position: QPoint) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        self.table.selectRow(index.row())
        menu = QMenu(self)
        menu.addAction(self.open_action)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closed = True
        super().closeEvent(event)
