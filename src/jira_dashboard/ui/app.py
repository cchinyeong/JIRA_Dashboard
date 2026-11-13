import logging
import sys
from collections.abc import Sequence

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

from jira_dashboard.config import Settings, get_settings
from jira_dashboard.integrations.jira_client import JiraClient, TicketBatch
from jira_dashboard.integrations.jira_onprem import JiraNotConfiguredError, JiraOnPremClient
from jira_dashboard.models import Ticket
from jira_dashboard.services.ticket_service import TicketService
from jira_dashboard.ui.main_window import NOT_CONFIGURED_URL, MainWindow
from jira_dashboard.utils.logging import configure_logging

logger = logging.getLogger(__name__)
SHUTDOWN_WAIT_MS = 5000


class _UnconfiguredClient(JiraClient):
    """Stands in for the Jira client until a Jira address is configured."""

    def get_ticket(self, key: str) -> Ticket:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)

    def get_tickets(self, keys: Sequence[str]) -> TicketBatch:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)

    def search_tickets(self, *, in_sprints_only: bool = False) -> TicketBatch:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)


def launch(
    settings: Settings, client: JiraClient | None = None, argv: Sequence[str] | None = None
) -> tuple[QApplication, MainWindow]:
    """Show the main window and schedule the first refresh; does not enter the event loop."""
    app = QApplication.instance() or QApplication(list(argv if argv is not None else sys.argv))
    configured = not settings.jira.is_placeholder
    if client is None:
        client = JiraOnPremClient(settings) if configured else _UnconfiguredClient()
    service = TicketService(client, settings)
    window = MainWindow(service, not_configured=None if configured else NOT_CONFIGURED_URL)
    window.show()
    QTimer.singleShot(0, window.start_refresh)
    return app, window


def run(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.logging)
    app, window = launch(settings, argv=argv)
    try:
        return app.exec()
    finally:
        QThreadPool.globalInstance().waitForDone(SHUTDOWN_WAIT_MS)
        logger.info("Dashboard closed")
