from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPalette

from jira_dashboard.models import Ticket

FINDING_TINT = QBrush(QColor(255, 244, 214))
UNKNOWN_BRUSH = QBrush(QColor(128, 128, 128))
# Tinted rows are light in every theme, so they need their own dark text colours.
TINTED_TEXT_BRUSH = QBrush(QColor(30, 30, 30))
TINTED_UNKNOWN_BRUSH = QBrush(QColor(110, 110, 110))


def finding_tooltip(ticket: Ticket) -> str | None:
    if not ticket.findings:
        return None
    lines = []
    for finding in ticket.findings:
        line = f"• {finding.message}"
        if finding.suggestion:
            line += f"\n   Suggestion: {finding.suggestion}"
        lines.append(line)
    return "\n".join(lines)


def _italic() -> QFont:
    font = QFont()
    font.setItalic(True)
    return font


def style_role(role: int, ticket: Ticket, unknown: bool, dimmed: bool = False) -> Any:
    """Font, foreground and background shared by the table and the hierarchy view.

    A dimmed row is a context entry that does not match the filter: no tint, disabled colour.
    """
    if dimmed:
        if role == Qt.ItemDataRole.FontRole:
            return _italic()
        if role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(QPalette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text))
        return None
    if role == Qt.ItemDataRole.BackgroundRole and ticket.findings:
        return FINDING_TINT
    if role == Qt.ItemDataRole.FontRole and unknown:
        return _italic()
    if role == Qt.ItemDataRole.ForegroundRole:
        if ticket.findings:
            return TINTED_UNKNOWN_BRUSH if unknown else TINTED_TEXT_BRUSH
        return UNKNOWN_BRUSH if unknown else None
    return None
