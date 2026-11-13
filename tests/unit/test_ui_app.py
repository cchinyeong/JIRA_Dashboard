import json
import threading
from pathlib import Path

import httpx
import pytest
from PySide6.QtWidgets import QDialog
from ticket_factory import make_ticket

from jira_dashboard.config import get_settings
from jira_dashboard.config.local_settings import ENV_BASE_URL, set_base_url
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations import JiraClient, TicketBatch
from jira_dashboard.integrations.jira_onprem import JiraOnPremClient
from jira_dashboard.services.secrets import JIRA_PAT, InMemorySecretStore, MissingSecretError
from jira_dashboard.ui.app import launch

FIXTURES = Path(__file__).parent / "fixtures"


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


class NoTokenClient(BlockingClient):
    def search_tickets(self, *, in_sprints_only: bool = False):
        self.calls += 1
        raise MissingSecretError(JIRA_PAT)


class FakeDialogs:
    """Stands in for the setup dialog factory; records calls and plays a scripted outcome."""

    def __init__(self, accept: bool = False, on_accept=None) -> None:
        self.accept = accept
        self.on_accept = on_accept
        self.calls = 0

    def __call__(self, settings, parent):
        outer = self

        class Dialog:
            def exec(self) -> int:
                outer.calls += 1
                if outer.accept and outer.on_accept:
                    outer.on_accept()
                return QDialog.DialogCode.Accepted if outer.accept else QDialog.DialogCode.Rejected

        return Dialog()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    monkeypatch.delenv(ENV_BASE_URL, raising=False)


def test_window_is_shown_before_the_first_refresh_finishes(qtbot, monkeypatch) -> None:
    monkeypatch.setenv(ENV_BASE_URL, "https://jira.example.com")
    client = BlockingClient()
    _, window = launch(get_settings(), client, dialog_factory=None)
    qtbot.addWidget(window)
    assert window.isVisible()
    qtbot.waitUntil(lambda: client.calls == 1, timeout=5000)
    assert not window.refresh_action.isEnabled()
    assert window.table.model().rowCount() == 0
    client.gate.set()
    qtbot.waitUntil(lambda: window.table.model().rowCount() == 1, timeout=5000)
    assert window.refresh_action.isEnabled()


def test_placeholder_address_prompts_and_a_cancelled_prompt_leaves_the_message(qtbot) -> None:
    dialogs = FakeDialogs(accept=False)
    _, window = launch(get_settings(), dialog_factory=dialogs)
    qtbot.addWidget(window)
    assert window.isVisible()
    qtbot.waitUntil(lambda: dialogs.calls == 1, timeout=3000)
    assert "jira.base_url" in window.message_label.text()
    assert window.stack.currentWidget() is window.message_page
    assert window.setup_button.isVisibleTo(window)
    assert not window.refresh_action.isEnabled()
    assert window.setup_action.isEnabled()


def test_setup_button_and_action_reopen_the_dialog(qtbot) -> None:
    dialogs = FakeDialogs(accept=False)
    _, window = launch(get_settings(), dialog_factory=dialogs)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: dialogs.calls == 1, timeout=3000)
    window.setup_button.click()
    window.setup_action.trigger()
    assert dialogs.calls == 3


def test_no_setup_without_a_dialog_factory(qtbot) -> None:
    _, window = launch(get_settings(), dialog_factory=None)
    qtbot.addWidget(window)
    assert not window.setup_action.isEnabled()
    assert not window.setup_button.isVisibleTo(window)


def test_missing_token_prompts_once(qtbot, monkeypatch) -> None:
    monkeypatch.setenv(ENV_BASE_URL, "https://jira.example.com")
    dialogs = FakeDialogs(accept=False)
    client = NoTokenClient()
    _, window = launch(get_settings(), client, dialog_factory=dialogs)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: dialogs.calls == 1, timeout=5000)
    assert window.stack.currentWidget() is window.message_page
    assert window.setup_button.isVisibleTo(window)
    assert window.refresh_action.isEnabled()
    window.start_refresh()
    qtbot.waitUntil(lambda: client.calls == 2 and window.refresh_action.isEnabled(), timeout=5000)
    assert dialogs.calls == 1


def search_response() -> httpx.Response:
    issue = json.loads((FIXTURES / "issue_cae_1558.json").read_text(encoding="utf-8"))
    body = {"startAt": 0, "maxResults": 100, "total": 1, "issues": [issue]}
    return httpx.Response(200, json=body)


def test_saved_setup_is_applied_without_restart(qtbot, tmp_path) -> None:
    requests: list[httpx.Request] = []
    store = InMemorySecretStore()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return search_response()

    def factory(settings):
        return JiraOnPremClient(settings, store, transport=httpx.MockTransport(handler))

    def save() -> None:
        store.set(JIRA_PAT, "tok-0123456789")
        set_base_url(tmp_path / "settings.local.toml", "https://jira.example.com")

    dialogs = FakeDialogs(accept=True, on_accept=save)
    _, window = launch(get_settings(), client_factory=factory, dialog_factory=dialogs)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.table.model().rowCount() == 1, timeout=5000)
    assert dialogs.calls == 1
    assert window.stack.currentWidget() is window.splitter
    assert window.refresh_action.isEnabled()
    assert {r.url.host for r in requests} == {"jira.example.com"}
    assert {r.method for r in requests} == {"GET"}
    assert all(r.headers["authorization"] == "Bearer tok-0123456789" for r in requests)
