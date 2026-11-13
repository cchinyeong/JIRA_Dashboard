from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel

from jira_dashboard.models import Ticket
from jira_dashboard.services.ticket_query import GroupedView, TreeNode
from jira_dashboard.ui.styling import finding_tooltip, style_role
from jira_dashboard.ui.ticket_model import (
    COLUMNS,
    TICKET_ROLE,
    cell_text,
    cell_unknown,
)

ORPHANS_TITLE = "Tasks without a parent"
_TABLE_COLUMNS = {column.title: index for index, column in enumerate(COLUMNS)}
# Hierarchy column title -> index of the table column it mirrors (None: key and summary).
HIERARCHY_COLUMNS: tuple[tuple[str, int | None], ...] = (
    ("Key / Summary", None),
    ("Type", _TABLE_COLUMNS["Type"]),
    ("Status", _TABLE_COLUMNS["Status"]),
    ("Assignee", _TABLE_COLUMNS["Assignee"]),
    ("Sprint", _TABLE_COLUMNS["Sprint"]),
    ("Target end", _TABLE_COLUMNS["Target end"]),
    ("Findings", _TABLE_COLUMNS["Findings"]),
)
_ROLES = (
    Qt.ItemDataRole.FontRole,
    Qt.ItemDataRole.ForegroundRole,
    Qt.ItemDataRole.BackgroundRole,
)


def _cell(ticket: Ticket, table_column: int | None, dimmed: bool) -> QStandardItem:
    if table_column is None:
        text, unknown = f"{ticket.jira_key}  {ticket.summary}", False
    else:
        text, unknown = cell_text(ticket, table_column), cell_unknown(ticket, table_column)
    item = QStandardItem(text)
    item.setEditable(False)
    item.setData(ticket, TICKET_ROLE)
    item.setToolTip(finding_tooltip(ticket) or "")
    for role in _ROLES:
        value = style_role(role, ticket, unknown, dimmed)
        if value is not None:
            item.setData(value, role)
    return item


def _row(ticket: Ticket, dimmed: bool) -> list[QStandardItem]:
    return [_cell(ticket, column, dimmed) for _title, column in HIERARCHY_COLUMNS]


def _add_node(parent: QStandardItem, node: TreeNode) -> None:
    row = _row(node.ticket, dimmed=not node.matched)
    parent.appendRow(row)
    for child in node.children:
        _add_node(row[0], child)


class HierarchyModel(QStandardItemModel):
    """Read-only tree of requests and their tasks built from a GroupedView."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reset_headers()

    def _reset_headers(self) -> None:
        self.setHorizontalHeaderLabels([title for title, _column in HIERARCHY_COLUMNS])

    def set_view(self, view: GroupedView) -> None:
        self.clear()
        self._reset_headers()
        root = self.invisibleRootItem()
        for node in view.roots:
            _add_node(root, node)
        if view.orphans:
            group = QStandardItem(f"{ORPHANS_TITLE} ({len(view.orphans)})")
            font = QFont()
            font.setBold(True)
            group.setFont(font)
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            root.appendRow([group, *[self._blank() for _ in HIERARCHY_COLUMNS[1:]]])
            for ticket in view.orphans:
                group.appendRow(_row(ticket, dimmed=False))

    @staticmethod
    def _blank() -> QStandardItem:
        item = QStandardItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        return item

    def index_for_key(self, key: str) -> QModelIndex | None:
        def search(parent: QStandardItem) -> QModelIndex | None:
            for row in range(parent.rowCount()):
                item = parent.child(row, 0)
                ticket = item.data(TICKET_ROLE)
                if ticket is not None and ticket.jira_key == key:
                    return item.index()
                found = search(item)
                if found is not None:
                    return found
            return None

        return search(self.invisibleRootItem())
