from collections.abc import Sequence

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from jira_dashboard.services.ticket_query import FacetValue, TicketFilter

DEBOUNCE_MS = 250
MENU_HEIGHT = 320
VIEW_TABLE = "table"
VIEW_HIERARCHY = "hierarchy"

# (button title, facet name, TicketFilter field)
FACET_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Type", "kind", "kinds"),
    ("Status", "status", "statuses"),
    ("Domain", "domain", "domains"),
    ("Dyson Project", "dyson_project", "dyson_projects"),
    ("Assignee", "assignee", "assignees"),
    ("Sprint", "sprint", "sprints"),
    ("Priority", "priority", "priorities"),
)


class FacetButton(QToolButton):
    """A button whose menu lists values with counts as check boxes; the menu stays open."""

    changed = Signal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._boxes: list[tuple[object, QCheckBox]] = []
        self._menu = QMenu(self)
        self.setMenu(self._menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._refresh_text()

    def selected(self) -> frozenset:
        return frozenset(value for value, box in self._boxes if box.isChecked())

    def entries(self) -> list[str]:
        return [box.text() for _, box in self._boxes]

    def set_checked(self, value: object, checked: bool = True) -> None:
        for candidate, box in self._boxes:
            if candidate == value:
                box.setChecked(checked)

    def clear_selection(self) -> None:
        for _, box in self._boxes:
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)
        self._refresh_text()

    def set_values(self, values: Sequence[FacetValue]) -> None:
        """Rebuilds the menu, keeping selected values that still exist."""
        keep = self.selected()
        self._menu.clear()
        self._boxes = []
        holder = QWidget()
        layout = QVBoxLayout(holder)
        for item in values:
            box = QCheckBox(f"{item.label} ({item.count})")
            box.setChecked(item.value in keep)
            box.toggled.connect(self._on_toggled)
            layout.addWidget(box)
            self._boxes.append((item.value, box))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(MENU_HEIGHT)
        scroll.setWidget(holder)
        action = QWidgetAction(self._menu)
        action.setDefaultWidget(scroll)
        self._menu.addAction(action)
        self._refresh_text()
        if self.selected() != keep:
            self.changed.emit()

    def _on_toggled(self, _checked: bool) -> None:
        self._refresh_text()
        self.changed.emit()

    def _refresh_text(self) -> None:
        count = len(self.selected())
        self.setText(f"{self._title} ({count})" if count else self._title)


class FilterBar(QWidget):
    changed = Signal(object)
    view_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None, debounce_ms: int = DEBOUNCE_MS) -> None:
        super().__init__(parent)
        self._last = TicketFilter()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search key, summary, requester, assignee")
        self.search.setClearButtonEnabled(True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._emit)
        self.search.textChanged.connect(self._timer.start)

        self.buttons: dict[str, FacetButton] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search, 1)
        for title, facet, _field in FACET_FIELDS:
            button = FacetButton(title)
            button.changed.connect(self._emit)
            self.buttons[facet] = button
            layout.addWidget(button)
        self.findings_only = QCheckBox("Only with findings")
        self.findings_only.toggled.connect(self._emit)
        layout.addWidget(self.findings_only)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)
        layout.addWidget(self.clear_button)

        self.table_button = self._view_button("Table", VIEW_TABLE)
        self.hierarchy_button = self._view_button("Hierarchy", VIEW_HIERARCHY)
        self.table_button.setChecked(True)
        layout.addWidget(self.table_button)
        layout.addWidget(self.hierarchy_button)

    def _view_button(self, text: str, view: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.toggled.connect(lambda checked: checked and self.view_changed.emit(view))
        return button

    @property
    def view(self) -> str:
        return VIEW_HIERARCHY if self.hierarchy_button.isChecked() else VIEW_TABLE

    def set_view(self, view: str) -> None:
        (self.hierarchy_button if view == VIEW_HIERARCHY else self.table_button).setChecked(True)

    def current_filter(self) -> TicketFilter:
        fields = {field: self.buttons[facet].selected() for _t, facet, field in FACET_FIELDS}
        return TicketFilter(
            text=self.search.text(), only_with_findings=self.findings_only.isChecked(), **fields
        )

    def is_active(self) -> bool:
        return self.current_filter() != TicketFilter()

    def set_facets(self, facets: dict[str, list[FacetValue]]) -> None:
        for facet, button in self.buttons.items():
            button.set_values(facets.get(facet, []))

    def clear(self) -> None:
        self._timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.findings_only.blockSignals(True)
        self.findings_only.setChecked(False)
        self.findings_only.blockSignals(False)
        for button in self.buttons.values():
            button.clear_selection()
        self._emit()

    def _emit(self, *_args) -> None:
        current = self.current_filter()
        if current != self._last:
            self._last = current
            self.changed.emit(current)
