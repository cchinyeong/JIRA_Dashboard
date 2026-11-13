from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from jira_dashboard.models import Finding, Ticket, TicketStatus
from jira_dashboard.ui.formatting import (
    UNKNOWN,
    domain_value,
    format_date,
    format_days,
    status_text,
)
from jira_dashboard.ui.jira_markup import to_html

HINT = "Select a ticket to see its details."
NO_FINDINGS = "No findings detected."

SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Overview", ("Status", "Type", "Priority", "Domain", "Request drivers")),
    ("People", ("Assignee", "Reporter", "Requester")),
    (
        "Planning",
        (
            "Dyson projects",
            "Sprint",
            "Target start",
            "Target end",
            "Actual start",
            "Completion",
            "Created",
            "Updated",
            "Estimated (days)",
            "Remaining (days)",
            "Blocked",
        ),
    ),
    ("Hierarchy", ("Parent",)),
)


def _date_or_none(value) -> str | None:
    return format_date(value) if value is not None else None


def _days_or_none(value: float | None) -> str | None:
    return format_days(value) if value is not None else None


def _sprint_text(ticket: Ticket) -> str | None:
    sprint = ticket.sprint
    if sprint is None:
        return None
    dates = [format_date(d) for d in (sprint.start_date, sprint.end_date) if d is not None]
    detail = ", ".join([sprint.state, " – ".join(dates)] if dates else [sprint.state])
    return f"{sprint.name} ({detail})"


def _blocked_text(ticket: Ticket) -> str:
    if not ticket.is_blocked:
        return "No"
    return f"Yes: {ticket.blocked_reason}" if ticket.blocked_reason else "Yes"


def _parent_text(ticket: Ticket, parent: Ticket | None) -> str:
    if not ticket.parent_key:
        return "None"
    if parent is None:
        return ticket.parent_key
    kind = f" · {parent.issue_type}" if parent.issue_type else ""
    return f"{ticket.parent_key}{kind} · {parent.summary}"


def finding_text(finding: Finding) -> str:
    lines = [finding.message]
    if finding.field:
        lines.append(f"Field: {finding.field}")
    if finding.related_key:
        lines.append(f"Related: {finding.related_key}")
    if finding.suggestion:
        lines.append(f"Suggestion: {finding.suggestion}")
    return "\n".join(lines)


class DetailsPanel(QWidget):
    """Read-only view of one ticket. All text is plain text; nothing is interpreted as markup."""

    open_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._labels: dict[str, QLabel] = {}
        self._finding_labels: list[QLabel] = []

        self.hint = QLabel(HINT)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)

        self.title = self._plain_label()
        font = self.title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.title.setFont(font)
        self.open_button = QPushButton("Open in Jira")
        self.open_button.clicked.connect(self.open_requested)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.addWidget(self.title)
        self._layout.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignLeft)
        for name, rows in SECTIONS:
            self._layout.addWidget(self._section(name, rows))

        self._findings_box = QGroupBox("Findings")
        self._findings_layout = QVBoxLayout(self._findings_box)
        self._layout.addWidget(self._findings_box)

        description_box = QGroupBox("Description")
        description_layout = QVBoxLayout(description_box)
        self.description = QTextBrowser()
        self.description.setReadOnly(True)
        self.description.setOpenLinks(False)
        self.description.setOpenExternalLinks(False)
        self.description.setMinimumHeight(180)
        description_layout.addWidget(self.description)
        self._layout.addWidget(description_box)
        self._layout.addStretch(1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.hint)
        outer.addWidget(self.scroll, 1)
        self.show_ticket(None, None, None)

    @staticmethod
    def _plain_label() -> QLabel:
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _section(self, name: str, rows: tuple[str, ...]) -> QGroupBox:
        box = QGroupBox(name)
        form = QFormLayout(box)
        for row in rows:
            label = self._plain_label()
            self._labels[row] = label
            form.addRow(row + ":", label)
        return box

    def _set(self, name: str, text: str | None, *, unknown: bool = False) -> None:
        self._style(self._labels[name], text, unknown)

    @staticmethod
    def _style(label: QLabel, text: str | None, unknown: bool = False) -> None:
        unknown = unknown or text is None
        label.setText(UNKNOWN if text is None else text)
        font = label.font()
        font.setItalic(unknown)
        label.setFont(font)
        # The palette's placeholder colour follows the active light or dark theme.
        label.setForegroundRole(
            QPalette.ColorRole.PlaceholderText if unknown else QPalette.ColorRole.WindowText
        )

    def value(self, name: str) -> str:
        return self._labels[name].text()

    def is_unknown(self, name: str) -> bool:
        return self._labels[name].font().italic()

    def finding_texts(self) -> list[str]:
        return [label.text() for label in self._finding_labels]

    def show_ticket(self, ticket: Ticket | None, parent: Ticket | None, link: str | None) -> None:
        has_ticket = ticket is not None
        self.hint.setVisible(not has_ticket)
        self.scroll.setVisible(has_ticket)
        self.open_button.setEnabled(has_ticket and link is not None)
        if ticket is None:
            self.title.setText("")
            return
        self.title.setText(f"{ticket.jira_key}  {ticket.summary}")
        self._set("Status", status_text(ticket), unknown=ticket.status is TicketStatus.UNKNOWN)
        self._set("Type", ticket.issue_type)
        self._set("Priority", ticket.priority)
        self._set("Domain", domain_value(ticket))
        self._set("Request drivers", ", ".join(ticket.request_drivers) or None)
        self._set("Assignee", ticket.assignee.display_name if ticket.assignee else None)
        self._set("Reporter", ticket.reporter.display_name if ticket.reporter else None)
        self._set("Requester", ticket.requester or None)
        self._set("Dyson projects", ", ".join(ticket.dyson_projects) or None)
        self._set("Sprint", _sprint_text(ticket))
        self._set("Target start", _date_or_none(ticket.target_start_date))
        self._set("Target end", _date_or_none(ticket.target_end_date))
        self._set("Actual start", _date_or_none(ticket.actual_start_date))
        self._set("Completion", _date_or_none(ticket.completion_date))
        self._set("Created", _date_or_none(ticket.created_date))
        self._set("Updated", _date_or_none(ticket.updated_date))
        self._set("Estimated (days)", _days_or_none(ticket.estimated_effort))
        self._set("Remaining (days)", _days_or_none(ticket.remaining_effort))
        self._set("Blocked", _blocked_text(ticket))
        self._set("Parent", _parent_text(ticket, parent))
        self._show_findings(ticket)
        if ticket.description:
            self.description.setHtml(to_html(ticket.description))
        else:
            self.description.setPlainText(UNKNOWN)
        font = self.description.font()
        font.setItalic(not ticket.description)
        self.description.setFont(font)

    def _show_findings(self, ticket: Ticket) -> None:
        for label in self._finding_labels:
            self._findings_layout.removeWidget(label)
            label.deleteLater()
        self._finding_labels = []
        texts = [finding_text(f) for f in ticket.findings] or [NO_FINDINGS]
        for text in texts:
            label = self._plain_label()
            label.setText(text)
            self._findings_layout.addWidget(label)
            self._finding_labels.append(label)
