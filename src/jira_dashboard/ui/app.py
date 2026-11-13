import logging
import sys
from collections.abc import Callable, Sequence

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from jira_dashboard.config import Settings, get_settings
from jira_dashboard.integrations.jira_client import JiraClient, TicketBatch
from jira_dashboard.integrations.jira_onprem import JiraNotConfiguredError, JiraOnPremClient
from jira_dashboard.models import Ticket
from jira_dashboard.services.ticket_service import TicketService
from jira_dashboard.ui.main_window import NOT_CONFIGURED_URL, DialogLike, MainWindow
from jira_dashboard.ui.setup_dialog import SetupDialog
from jira_dashboard.utils.logging import configure_logging

logger = logging.getLogger(__name__)
SHUTDOWN_WAIT_MS = 5000

ClientFactory = Callable[[Settings], JiraClient]
DialogFactory = Callable[[Settings, QWidget], DialogLike]


class _UnconfiguredClient(JiraClient):
    """Stands in for the Jira client until a Jira address is configured."""

    def get_ticket(self, key: str) -> Ticket:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)

    def get_tickets(self, keys: Sequence[str]) -> TicketBatch:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)

    def search_tickets(self, *, in_sprints_only: bool = False) -> TicketBatch:
        raise JiraNotConfiguredError(NOT_CONFIGURED_URL)


def _default_client(settings: Settings) -> JiraClient:
    return JiraOnPremClient(settings)


def _default_dialog(settings: Settings, parent: QWidget) -> DialogLike:
    return SetupDialog(settings, parent=parent)


class _Runtime:
    """Builds the client and service from settings, and rebuilds them after a setup change."""

    def __init__(self, settings: Settings, client: JiraClient | None, factory: ClientFactory):
        self.settings = settings
        self._factory = factory
        self._client = client

    def build(self) -> tuple[TicketService, str | None]:
        configured = not self.settings.jira.is_placeholder
        if self._client is None:
            self._client = self._factory(self.settings) if configured else _UnconfiguredClient()
        not_configured = None if configured else NOT_CONFIGURED_URL
        return TicketService(self._client, self.settings), not_configured

    def rebuild(self) -> tuple[TicketService, str | None]:
        old, self._client = self._client, None
        if old is not None and hasattr(old, "close"):
            old.close()
        self.settings = get_settings()
        return self.build()


def launch(
    settings: Settings,
    client: JiraClient | None = None,
    argv: Sequence[str] | None = None,
    *,
    client_factory: ClientFactory = _default_client,
    dialog_factory: DialogFactory | None = _default_dialog,
) -> tuple[QApplication, MainWindow]:
    """Show the main window and schedule the first step; does not enter the event loop.

    With a placeholder address the setup dialog opens first; otherwise a refresh starts.
    """
    app = QApplication.instance() or QApplication(list(argv if argv is not None else sys.argv))
    runtime = _Runtime(settings, client, client_factory)
    service, not_configured = runtime.build()
    window = MainWindow(
        service,
        not_configured=not_configured,
        reconfigure=runtime.rebuild,
        dialog_factory=(
            None
            if dialog_factory is None
            else lambda parent: dialog_factory(runtime.settings, parent)
        ),
    )
    window.show()
    QTimer.singleShot(0, window.open_setup if not_configured is not None else window.start_refresh)
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
