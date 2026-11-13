from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt

from jira_dashboard.ui.ticket_model import SORT_ROLE


class TicketSortProxy(QSortFilterProxyModel):
    """Sorts on SORT_ROLE and keeps unknown values after known ones in both directions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_unknown, left_value = left.data(SORT_ROLE)
        right_unknown, right_value = right.data(SORT_ROLE)
        if left_unknown != right_unknown:
            # Qt flips the result for descending order, so flip it back here.
            ascending = self.sortOrder() == Qt.SortOrder.AscendingOrder
            return right_unknown if ascending else left_unknown
        if left_unknown:
            return False
        return left_value < right_value
