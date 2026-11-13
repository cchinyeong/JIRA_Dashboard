import threading

import pytest
from ticket_factory import make_ticket

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations import JiraClient, TicketBatch
from jira_dashboard.ui.app import launch


class BlockingClient(JiraClient):
    def __init__(self) -> None:
        self.gate = threading.Event()
        self.calls = 0

    def get_ticket(self, key):
        raise NotImplementedError

    def get_tickets(self, keys):
        return TicketBatch()

    def search_tickets(self, *, in_sprints_only: bool = False):
        self.calls += 1
        assert self.gate.wait(5)
        return TicketBatch(tickets=[make_ticket("CAE-1")])


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    monkeypatch.delenv("JIRA_DASHBOARD_JIRA__BASE_URL", raising=False)


def test_window_is_shown_before_the_first_refresh_finishes(qtbot, monkeypatch) -> None:
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://jira.example.com")
    client = BlockingClient()
    _, window = launch(get_settings(), client)
    qtbot.addWidget(window)
    assert window.isVisible()
    qtbot.waitUntil(lambda: client.calls == 1, timeout=5000)
    assert not window.refresh_action.isEnabled()
    assert window.table.model().rowCount() == 0
    client.gate.set()
    qtbot.waitUntil(lambda: window.table.model().rowCount() == 1, timeout=5000)
    assert window.refresh_action.isEnabled()


def test_placeholder_address_starts_in_not_configured_state(qtbot) -> None:
    _, window = launch(get_settings())
    qtbot.addWidget(window)
    assert window.isVisible()
    assert "jira.base_url" in window.message_label.text()
    assert not window.refresh_action.isEnabled()
