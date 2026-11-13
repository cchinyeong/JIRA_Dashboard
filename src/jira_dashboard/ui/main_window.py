import logging
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Slot,
)
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QToolBar,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from jira_dashboard.models import Ticket
from jira_dashboard.services.ticket_query import GroupedView, TicketFilter
from jira_dashboard.services.ticket_service import RefreshResult, TicketService
from jira_dashboard.ui.details_panel import DetailsPanel
from jira_dashboard.ui.filter_bar import VIEW_HIERARCHY, FilterBar
from jira_dashboard.ui.hierarchy_model import HierarchyModel
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
NO_MATCH = "No ticket matches the filters. Press Clear to remove them."
SUMMARY_COLUMN = 1
MAX_SUMMARY_WIDTH = 420
MAX_TREE_KEY_WIDTH = 520

_ERROR_STYLE = "background:#fde7e9; color:#7a1f24; padding:6px;"
_WARNING_STYLE = "background:#fff4ce; color:#5c4400; padding:6px;"


def open_in_browser(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class DialogLike(Protocol):
    def exec(self) -> int: ...


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: TicketService,
        *,
        opener: Callable[[str], object] = open_in_browser,
        not_configured: str | None = None,
        pool: QThreadPool | None = None,
        reconfigure: Callable[[], tuple[TicketService, str | None]] | None = None,
        dialog_factory: Callable[[QWidget], DialogLike] | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._opener = opener
        self._pool = pool or QThreadPool.globalInstance()
        self._reconfigure = reconfigure
        self._dialog_factory = dialog_factory
        self._busy = False
        self._closed = False
        self._pending_swap = False
        self._auto_prompted = False
        self._configured = not_configured is None
        self._filter = TicketFilter()
        self._applying = False
        self._has_data = False
        self.setWindowTitle("VE Jira Operations Dashboard")
        self.resize(1400, 800)

        self._model = TicketTableModel(self)
        self._proxy = TicketSortProxy(self)
        self._proxy.setSourceModel(self._model)
        self._hierarchy = HierarchyModel(self)

        self._build_actions()
        self._build_central()
        self._build_status_bar()

        if not_configured is not None:
            self._show_message(not_configured, setup=True)
        self._update_actions()

    def _build_actions(self) -> None:
        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.refresh_action.triggered.connect(self.start_refresh)
        self.open_action = QAction("Open in Jira", self)
        self.open_action.triggered.connect(self.open_selected)
        self.setup_action = QAction("Jira setup…", self)
        self.setup_action.triggered.connect(self.open_setup)
        self.setup_action.setEnabled(self._dialog_factory is not None)
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.setup_action)
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
        self.table.customContextMenuRequested.connect(
            lambda position: self._show_context_menu(self.table, position)
        )
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.selectionModel().selectionChanged.connect(self._update_actions)

        self.tree = QTreeView()
        self.tree.setModel(self._hierarchy)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(
            lambda position: self._show_context_menu(self.tree, position)
        )
        self.tree.doubleClicked.connect(self._on_double_clicked)
        self.tree.selectionModel().selectionChanged.connect(self._update_actions)

        self.views = QStackedWidget()
        self.views.addWidget(self.table)
        self.views.addWidget(self.tree)

        self.filter_bar = FilterBar()
        self.filter_bar.changed.connect(self._on_filter_changed)
        self.filter_bar.view_changed.connect(self._on_view_changed)
        self.filter_bar.hide()

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setMargin(40)
        self.setup_button = QPushButton("Set up Jira…")
        self.setup_button.clicked.connect(self.open_setup)
        self.message_page = QWidget()
        message_layout = QVBoxLayout(self.message_page)
        message_layout.addStretch(1)
        message_layout.addWidget(self.message_label)
        message_layout.addWidget(self.setup_button, 0, Qt.AlignmentFlag.AlignCenter)
        message_layout.addStretch(1)

        self.details = DetailsPanel()
        self.details.open_requested.connect(self.open_selected)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.views)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([980, 420])

        self.stack = QStackedWidget()
        self.stack.addWidget(self.splitter)
        self.stack.addWidget(self.message_page)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.banner)
        layout.addWidget(self.filter_bar)
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

    @property
    def _hierarchy_shown(self) -> bool:
        return self.views.currentWidget() is self.tree

    def _selected_ticket(self) -> Ticket | None:
        view = self.tree if self._hierarchy_shown else self.table
        indexes = view.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].data(TICKET_ROLE)

    def _link_for(self, ticket: Ticket | None) -> str | None:
        return self._service.ticket_link(ticket) if ticket is not None else None

    def _update_actions(self, *_args) -> None:
        self.refresh_action.setEnabled(self._configured and not self._busy)
        ticket = self._selected_ticket()
        link = self._link_for(ticket)
        self.open_action.setEnabled(link is not None)
        parent = self._service.snapshot.get(ticket.parent_key) if ticket is not None else None
        self.details.show_ticket(ticket, parent, link)

    def _reselect(self, key: str | None) -> None:
        self.table.clearSelection()
        self.tree.clearSelection()
        if key is not None:
            if self._hierarchy_shown:
                index = self._hierarchy.index_for_key(key)
                if index is not None:
                    self.tree.selectionModel().select(
                        index,
                        QItemSelectionModel.SelectionFlag.ClearAndSelect
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
            else:
                for row in range(self._proxy.rowCount()):
                    if self._proxy.index(row, KEY_COLUMN).data(TICKET_ROLE).jira_key == key:
                        self.table.selectRow(row)
                        break
        self._update_actions()

    def _on_view_changed(self, view: str) -> None:
        selected = self._selected_ticket()
        self.views.setCurrentWidget(self.tree if view == VIEW_HIERARCHY else self.table)
        self._reselect(selected.jira_key if selected is not None else None)

    def _on_filter_changed(self, criteria: TicketFilter) -> None:
        if self._applying:
            return
        self._filter = criteria
        if self._has_data:
            self._rebuild()

    def _rebuild(self) -> None:
        selected = self._selected_ticket()
        shown = self._service.list_tickets(self._filter)
        self._model.set_tickets(shown)
        self._hierarchy.set_view(self._service.grouped(shown))
        self.tree.expandAll()
        self._size_columns()
        total = self._service.summary().total
        if not shown and total:
            self._show_message(NO_MATCH)
        else:
            self.stack.setCurrentWidget(self.splitter)
        self._reselect(selected.jira_key if selected is not None else None)
        self._update_summary(len(shown))

    def _size_columns(self) -> None:
        self.table.resizeColumnsToContents()
        if self.table.columnWidth(SUMMARY_COLUMN) > MAX_SUMMARY_WIDTH:
            self.table.setColumnWidth(SUMMARY_COLUMN, MAX_SUMMARY_WIDTH)
        for column in range(self._hierarchy.columnCount()):
            self.tree.resizeColumnToContents(column)
        if self.tree.columnWidth(0) > MAX_TREE_KEY_WIDTH:
            self.tree.setColumnWidth(0, MAX_TREE_KEY_WIDTH)

    def _update_summary(self, shown: int) -> None:
        summary = self._service.summary()
        count = f"{shown} of {summary.total}" if self.filter_bar.is_active() else str(summary.total)
        parts = [f"{count} tickets"]
        if summary.refreshed_at is not None:
            parts.append(f"refreshed {summary.refreshed_at.astimezone():%H:%M}")
        parts.append(f"{summary.unreadable} unreadable")
        parts.append(f"{summary.with_findings} with findings")
        self.summary_label.setText(" · ".join(parts))

    def _show_message(self, text: str, *, setup: bool = False) -> None:
        self.message_label.setText(text)
        self.setup_button.setVisible(setup and self._dialog_factory is not None)
        self.stack.setCurrentWidget(self.message_page)

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
        if self._pending_swap:
            self._pending_swap = False
            self._swap_service()
            return
        if result.ok:
            self._apply_success(result)
        elif result.error_kind == "no_token":
            self._show_message(f"{result.message}\n\n{NO_TOKEN_HELP}", setup=True)
            self.banner.hide()
            if not self._auto_prompted and self._dialog_factory is not None:
                self._auto_prompted = True
                QTimer.singleShot(0, self.open_setup)
        elif result.status == "failed":
            suffix = " Showing the previous data." if self._model.rowCount() else ""
            self._show_banner(f"Refresh failed: {result.message}{suffix}", _ERROR_STYLE)
        self._update_actions()

    def _apply_success(self, result: RefreshResult) -> None:
        self._applying = True
        try:
            self.filter_bar.set_facets(self._service.facets())
        finally:
            self._applying = False
        self._filter = self.filter_bar.current_filter()
        self._has_data = True
        self.filter_bar.show()
        self._rebuild()
        if result.warnings:
            self._show_banner("\n".join(result.warnings), _WARNING_STYLE)
        else:
            self.banner.hide()

    def open_selected(self) -> None:
        link = self._link_for(self._selected_ticket())
        if link is not None:
            self._opener(link)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        link = self._link_for(index.data(TICKET_ROLE))
        if link is not None:
            self._opener(link)

    def _show_context_menu(self, view: QAbstractItemView, position: QPoint) -> None:
        index = view.indexAt(position)
        if not index.isValid() or index.data(TICKET_ROLE) is None:
            return
        view.selectionModel().select(
            index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        menu = QMenu(self)
        menu.addAction(self.open_action)
        menu.exec(view.viewport().mapToGlobal(position))

    def open_setup(self) -> None:
        """Opens the Jira setup dialog; on save the new settings are applied without a restart."""
        if self._dialog_factory is None or self._closed:
            return
        dialog = self._dialog_factory(self)
        if not dialog.exec():
            return
        if self._busy:
            self._pending_swap = True
        else:
            self._swap_service()

    def _swap_service(self) -> None:
        if self._reconfigure is None:
            return
        service, not_configured = self._reconfigure()
        self.set_service(service, not_configured)

    def set_service(self, service: TicketService, not_configured: str | None = None) -> None:
        """Replaces the service (after a setup change), clears old data and refreshes."""
        self._service = service
        self._configured = not_configured is None
        self._has_data = False
        self._applying = True
        try:
            self.filter_bar.clear()
            self.filter_bar.set_facets({})
        finally:
            self._applying = False
        self._filter = TicketFilter()
        self.filter_bar.hide()
        self._model.set_tickets([])
        self._hierarchy.set_view(GroupedView(roots=[], orphans=[]))
        self.banner.hide()
        self.summary_label.setText("No data yet")
        self._auto_prompted = False
        if not_configured is not None:
            self._show_message(not_configured, setup=True)
            self._update_actions()
            return
        self.stack.setCurrentWidget(self.splitter)
        self._update_actions()
        self.start_refresh()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closed = True
        super().closeEvent(event)
