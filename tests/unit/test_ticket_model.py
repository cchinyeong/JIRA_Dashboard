from datetime import date

from PySide6.QtCore import QModelIndex, Qt
from ticket_factory import make_ticket

from jira_dashboard.models import (
    Domain,
    Finding,
    FindingCode,
    Ticket,
    TicketStatus,
    User,
)
from jira_dashboard.ui.sort_proxy import TicketSortProxy
from jira_dashboard.ui.ticket_model import COLUMNS, TicketTableModel


def column(title: str) -> int:
    return [c.title for c in COLUMNS].index(title)


def text(model, row: int, title: str) -> str:
    return model.index(row, column(title)).data(Qt.ItemDataRole.DisplayRole)


def model_with(*tickets: Ticket) -> TicketTableModel:
    model = TicketTableModel()
    model.set_tickets(list(tickets))
    return model


def test_columns_in_order() -> None:
    assert [c.title for c in COLUMNS] == [
        "Key",
        "Summary",
        "Type",
        "Status",
        "Priority",
        "Assignee",
        "Domain",
        "Sprint",
        "Target end",
        "Remaining (days)",
        "Findings",
        "Updated",
    ]


def test_known_values() -> None:
    model = model_with(make_ticket())
    assert text(model, 0, "Key") == "CAE-1"
    assert text(model, 0, "Status") == "In Progress"
    assert text(model, 0, "Assignee") == "Ann"
    assert text(model, 0, "Domain") == "Cfd"
    assert text(model, 0, "Sprint") == "Sprint 1"
    assert text(model, 0, "Target end") == "05 Nov 2026"
    assert text(model, 0, "Remaining (days)") == "2.5"
    assert text(model, 0, "Updated") == "01 Nov 2026"
    assert text(model, 0, "Findings") == ""


def test_unknown_values_use_unknown_style() -> None:
    model = model_with(
        make_ticket(assignee=None, sprint=None, remaining_effort=None, domain=Domain.UNSPECIFIED)
    )
    for title in ("Assignee", "Sprint", "Remaining (days)", "Domain"):
        index = model.index(0, column(title))
        assert index.data(Qt.ItemDataRole.DisplayRole) == "Unknown"
        assert index.data(Qt.ItemDataRole.FontRole).italic()
    known = model.index(0, column("Priority"))
    assert known.data(Qt.ItemDataRole.FontRole) is None


def test_non_standard_status_shows_raw_name() -> None:
    model = model_with(make_ticket(status=TicketStatus.UNKNOWN, raw_status="Implemented"))
    assert text(model, 0, "Status") == "Unknown (Implemented)"


def test_findings_count_tint_and_tooltip() -> None:
    finding = Finding(
        FindingCode.TASK_WITHOUT_PARENT, "No parent.", suggestion="Link it to an Epic."
    )
    model = model_with(make_ticket("CAE-1", findings=(finding,)), make_ticket("CAE-2"))
    index = model.index(0, column("Findings"))
    assert index.data(Qt.ItemDataRole.DisplayRole) == "1"
    assert index.data(Qt.ItemDataRole.BackgroundRole) is not None
    tooltip = index.data(Qt.ItemDataRole.ToolTipRole)
    assert "No parent." in tooltip and "Link it to an Epic." in tooltip
    clean = model.index(1, column("Findings"))
    assert clean.data(Qt.ItemDataRole.BackgroundRole) is None
    assert clean.data(Qt.ItemDataRole.ForegroundRole) is None
    assert index.data(Qt.ItemDataRole.ForegroundRole).color().lightness() < 100
    assert clean.data(Qt.ItemDataRole.ToolTipRole) is None


def test_cells_are_not_editable() -> None:
    model = model_with(make_ticket())
    index = model.index(0, 0)
    assert not model.flags(index) & Qt.ItemFlag.ItemIsEditable
    assert not model.setData(index, "changed")
    assert text(model, 0, "Key") == "CAE-1"


def proxy_for(*tickets: Ticket) -> TicketSortProxy:
    model = model_with(*tickets)
    proxy = TicketSortProxy()
    proxy.setSourceModel(model)
    return proxy


def keys(proxy: TicketSortProxy) -> list[str]:
    return [proxy.index(row, 0).data() for row in range(proxy.rowCount(QModelIndex()))]


def test_key_sorts_numerically() -> None:
    proxy = proxy_for(make_ticket("CAE-100"), make_ticket("CAE-99"), make_ticket("CAE-7"))
    proxy.sort(column("Key"), Qt.SortOrder.AscendingOrder)
    assert keys(proxy) == ["CAE-7", "CAE-99", "CAE-100"]


def test_unknown_assignee_last_in_both_directions() -> None:
    nobody = make_ticket("CAE-1", assignee=None)
    ann = make_ticket("CAE-2", assignee=User(username="a", display_name="Ann"))
    bob = make_ticket("CAE-3", assignee=User(username="b", display_name="Bob"))
    proxy = proxy_for(nobody, bob, ann)
    proxy.sort(column("Assignee"), Qt.SortOrder.AscendingOrder)
    assert keys(proxy) == ["CAE-2", "CAE-3", "CAE-1"]
    proxy.sort(column("Assignee"), Qt.SortOrder.DescendingOrder)
    assert keys(proxy) == ["CAE-3", "CAE-2", "CAE-1"]


def test_sort_by_remaining_and_target_end() -> None:
    a = make_ticket("CAE-1", remaining_effort=10.0, target_end_date=date(2026, 12, 1))
    b = make_ticket("CAE-2", remaining_effort=2.0, target_end_date=date(2026, 11, 1))
    c = make_ticket("CAE-3", remaining_effort=None, target_end_date=None)
    proxy = proxy_for(a, b, c)
    proxy.sort(column("Remaining (days)"), Qt.SortOrder.AscendingOrder)
    assert keys(proxy) == ["CAE-2", "CAE-1", "CAE-3"]
    proxy.sort(column("Target end"), Qt.SortOrder.DescendingOrder)
    assert keys(proxy) == ["CAE-1", "CAE-2", "CAE-3"]
