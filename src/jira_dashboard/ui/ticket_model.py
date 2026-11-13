import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from jira_dashboard.models import Domain, Ticket, TicketStatus

UNKNOWN = "Unknown"
SORT_ROLE = Qt.ItemDataRole.UserRole + 1
TICKET_ROLE = Qt.ItemDataRole.UserRole + 2
FINDING_TINT = QBrush(QColor(255, 244, 214))
UNKNOWN_BRUSH = QBrush(QColor(128, 128, 128))
# Tinted rows are light in every theme, so they need their own dark text colours.
TINTED_TEXT_BRUSH = QBrush(QColor(30, 30, 30))
TINTED_UNKNOWN_BRUSH = QBrush(QColor(110, 110, 110))

_KEY_PATTERN = re.compile(r"^(.*?)-(\d+)$")
_Value = tuple[bool, Any]
_ModelIndex = QModelIndex | QPersistentModelIndex
_NO_PARENT = QModelIndex()


@dataclass(frozen=True, slots=True)
class Column:
    title: str
    value: Any  # Ticket -> raw value or None when unknown
    text: Any  # raw value -> display text


def _format_date(value: date | datetime) -> str:
    return f"{value.day:02d} {value:%b %Y}"


def _format_days(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _key_sort(ticket: Ticket) -> tuple[str, int]:
    match = _KEY_PATTERN.match(ticket.jira_key)
    if match is None:
        return (ticket.jira_key, 0)
    return (match.group(1), int(match.group(2)))


def _status_text(ticket: Ticket) -> str:
    if ticket.status is TicketStatus.UNKNOWN:
        return f"{UNKNOWN} ({ticket.raw_status})" if ticket.raw_status else UNKNOWN
    return ticket.status.value.replace("_", " ").title()


def _domain(ticket: Ticket) -> str | None:
    if ticket.domain is Domain.UNSPECIFIED:
        return None
    return ticket.domain.value.title()


COLUMNS: tuple[Column, ...] = (
    Column("Key", lambda t: t.jira_key, str),
    Column("Summary", lambda t: t.summary or None, str),
    Column("Type", lambda t: t.issue_type, str),
    Column("Status", lambda t: None if t.status is TicketStatus.UNKNOWN else t.status, None),
    Column("Priority", lambda t: t.priority, str),
    Column("Assignee", lambda t: t.assignee.display_name if t.assignee else None, str),
    Column("Domain", _domain, str),
    Column("Sprint", lambda t: t.sprint.name if t.sprint else None, str),
    Column("Target end", lambda t: t.target_end_date, _format_date),
    Column("Remaining (days)", lambda t: t.remaining_effort, _format_days),
    Column("Findings", lambda t: len(t.findings) or None, str),
    Column("Updated", lambda t: t.updated_date, _format_date),
)
KEY_COLUMN = 0
STATUS_COLUMN = 3
FINDINGS_COLUMN = 10


def _tooltip(ticket: Ticket) -> str | None:
    if not ticket.findings:
        return None
    lines = []
    for finding in ticket.findings:
        line = f"• {finding.message}"
        if finding.suggestion:
            line += f"\n   Suggestion: {finding.suggestion}"
        lines.append(line)
    return "\n".join(lines)


class TicketTableModel(QAbstractTableModel):
    """Read-only table of tickets."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tickets: list[Ticket] = []

    def set_tickets(self, tickets: list[Ticket]) -> None:
        self.beginResetModel()
        self._tickets = list(tickets)
        self.endResetModel()

    def ticket_at(self, row: int) -> Ticket:
        return self._tickets[row]

    def rowCount(self, parent: _ModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(self._tickets)

    def columnCount(self, parent: _ModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section].title
        return None

    def flags(self, index: _ModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def _is_unknown(self, ticket: Ticket, column: int) -> bool:
        return COLUMNS[column].value(ticket) is None and column != FINDINGS_COLUMN

    def _display(self, ticket: Ticket, column: int) -> str:
        if column == STATUS_COLUMN:
            return _status_text(ticket)
        raw = COLUMNS[column].value(ticket)
        if raw is None:
            return "" if column == FINDINGS_COLUMN else UNKNOWN
        return COLUMNS[column].text(raw)

    def sort_value(self, ticket: Ticket, column: int) -> _Value:
        if column == KEY_COLUMN:
            return (False, _key_sort(ticket))
        raw = COLUMNS[column].value(ticket)
        if raw is None:
            return (column != FINDINGS_COLUMN, 0)
        if column == STATUS_COLUMN:
            return (False, list(TicketStatus).index(raw))
        if isinstance(raw, str):
            return (False, raw.casefold())
        return (False, raw)

    def data(self, index: _ModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        ticket = self._tickets[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(ticket, column)
        if role == SORT_ROLE:
            return self.sort_value(ticket, column)
        if role == TICKET_ROLE:
            return ticket
        if role == Qt.ItemDataRole.ToolTipRole:
            return _tooltip(ticket)
        if role == Qt.ItemDataRole.BackgroundRole and ticket.findings:
            return FINDING_TINT
        unknown = self._is_unknown(ticket, column)
        if role == Qt.ItemDataRole.FontRole and unknown:
            font = QFont()
            font.setItalic(True)
            return font
        if role == Qt.ItemDataRole.ForegroundRole:
            if ticket.findings:
                return TINTED_UNKNOWN_BRUSH if unknown else TINTED_TEXT_BRUSH
            return UNKNOWN_BRUSH if unknown else None
        return None
