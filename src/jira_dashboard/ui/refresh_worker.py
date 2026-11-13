import logging

from PySide6.QtCore import QObject, QRunnable, Signal

from jira_dashboard.services.ticket_service import STATUS_FAILED, RefreshResult, TicketService

logger = logging.getLogger(__name__)


class RefreshSignals(QObject):
    finished = Signal(object)


class RefreshWorker(QRunnable):
    """Runs TicketService.refresh() on a pool thread and reports the result by signal."""

    def __init__(self, service: TicketService) -> None:
        super().__init__()
        self._service = service
        self.signals = RefreshSignals()

    def run(self) -> None:
        try:
            result = self._service.refresh()
        except Exception:
            logger.exception("Refresh worker failed unexpectedly")
            result = RefreshResult(
                STATUS_FAILED,
                error_kind="unexpected",
                message="Unexpected error while refreshing. See the log for details.",
            )
        self.signals.finished.emit(result)
