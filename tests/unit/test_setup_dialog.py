import logging
import threading

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.local_settings import ENV_BASE_URL
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.services.connection_test import ConnectionResult
from jira_dashboard.services.secrets import JIRA_PAT, InMemorySecretStore
from jira_dashboard.ui.setup_dialog import (
    ENV_OVERRIDE_NOTE,
    TOKEN_MISSING_HINT,
    TOKEN_STORED_HINT,
    SetupDialog,
)

TOKEN = "pat-secret-abcdefghij"
GOOD = ConnectionResult(True, "ok", "Connected as CY Chong.", "CY Chong")
BAD = ConnectionResult(False, "rejected", "Jira did not accept the token.")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    monkeypatch.delenv(ENV_BASE_URL, raising=False)


class FakeTester:
    def __init__(self, result=GOOD, gate: threading.Event | None = None) -> None:
        self.result = result
        self.gate = gate
        self.calls: list[tuple[str, str, threading.Thread]] = []

    def __call__(self, settings, address, token):
        self.calls.append((address, token.get_secret_value(), threading.current_thread()))
        if self.gate is not None:
            assert self.gate.wait(5)
        return self.result


def make(qtbot, tmp_path, *, store=None, tester=None, answers=(True,), settings=None):
    asked: list[str] = []
    replies = list(answers)

    def confirm(text: str) -> bool:
        asked.append(text)
        return replies.pop(0)

    dialog = SetupDialog(
        settings or get_settings(),
        secret_store=store if store is not None else InMemorySecretStore(),
        tester=tester or FakeTester(),
        settings_path=tmp_path / "settings.local.toml",
        confirm=confirm,
    )
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.asked = asked
    return dialog


def fill(dialog, address="https://jira.example.com", token=TOKEN) -> None:
    dialog.address_edit.setText(address)
    dialog.token_edit.setText(token)


def settings_file(tmp_path):
    return tmp_path / "settings.local.toml"


def test_first_run_state(qtbot, tmp_path) -> None:
    dialog = make(qtbot, tmp_path)
    assert dialog.address_edit.text() == ""
    assert dialog.token_edit.placeholderText() == TOKEN_MISSING_HINT
    assert not dialog.save_button.isEnabled() and not dialog.test_button.isEnabled()


def test_token_field_is_masked(qtbot, tmp_path) -> None:
    from PySide6.QtWidgets import QLineEdit

    assert make(qtbot, tmp_path).token_edit.echoMode() == QLineEdit.EchoMode.Password


def test_opened_later_shows_address_and_token_stored(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_BASE_URL, "https://jira.example.com")
    settings = get_settings()
    monkeypatch.delenv(ENV_BASE_URL)
    store = InMemorySecretStore()
    store.set(JIRA_PAT, TOKEN)
    dialog = make(qtbot, tmp_path, store=store, settings=settings)
    assert dialog.address_edit.text() == "https://jira.example.com"
    assert dialog.token_edit.placeholderText() == TOKEN_STORED_HINT
    assert dialog.token_edit.text() == "" and TOKEN not in dialog.status_label.text()
    assert dialog.save_button.isEnabled()


@pytest.mark.parametrize(
    ("address", "fragment"),
    [
        ("http://jira.example.com", "https"),
        ("https://u:hunter2@jira.example.com", "user name"),
        ("https://jira.invalid", "placeholder"),
    ],
)
def test_rejected_addresses_explain_and_block_saving(qtbot, tmp_path, address, fragment) -> None:
    dialog = make(qtbot, tmp_path)
    fill(dialog, address)
    assert fragment in dialog.status_label.text()
    assert "hunter2" not in dialog.status_label.text()
    assert not dialog.save_button.isEnabled() and not dialog.test_button.isEnabled()


def test_save_needs_an_available_token(qtbot, tmp_path) -> None:
    dialog = make(qtbot, tmp_path)
    fill(dialog, token="")
    assert not dialog.save_button.isEnabled()
    dialog.token_edit.setText("x")
    assert dialog.save_button.isEnabled()


def test_successful_test_keeps_the_dialog_responsive_and_enables_quiet_save(
    qtbot, tmp_path
) -> None:
    gate = threading.Event()
    tester = FakeTester(GOOD, gate)
    dialog = make(qtbot, tmp_path, tester=tester)
    fill(dialog)
    dialog.test_button.click()
    assert "Testing" in dialog.status_label.text()
    assert not dialog.test_button.isEnabled()
    dialog.address_edit.setText("https://other.example.com")
    dialog.address_edit.setText("https://jira.example.com")
    gate.set()
    qtbot.waitUntil(lambda: dialog.test_button.isEnabled(), timeout=5000)
    assert tester.calls[0][2] is not threading.main_thread()
    assert tester.calls[0][:2] == ("https://jira.example.com", TOKEN)
    # the result belonged to older inputs, so it must be discarded
    assert dialog.status_label.text() == ""
    dialog.test_button.click()
    qtbot.waitUntil(lambda: "Connected as CY Chong." in dialog.status_label.text(), timeout=5000)


def test_failed_test_message_is_shown_without_the_token(qtbot, tmp_path) -> None:
    dialog = make(qtbot, tmp_path, tester=FakeTester(BAD))
    fill(dialog)
    dialog.test_button.click()
    qtbot.waitUntil(lambda: "did not accept" in dialog.status_label.text(), timeout=5000)
    assert TOKEN not in dialog.status_label.text()


def test_test_uses_the_stored_token_when_the_field_is_empty(qtbot, tmp_path) -> None:
    store = InMemorySecretStore()
    store.set(JIRA_PAT, "stored-token-0123456789")
    tester = FakeTester()
    dialog = make(qtbot, tmp_path, store=store, tester=tester)
    fill(dialog, token="")
    dialog.test_button.click()
    qtbot.waitUntil(lambda: bool(tester.calls), timeout=5000)
    assert tester.calls[0][1] == "stored-token-0123456789"


def test_save_after_successful_test_stores_token_and_address(qtbot, tmp_path) -> None:
    store = InMemorySecretStore()
    dialog = make(qtbot, tmp_path, store=store)
    fill(dialog)
    dialog.test_button.click()
    qtbot.waitUntil(lambda: "Connected" in dialog.status_label.text(), timeout=5000)
    dialog.save_button.click()
    assert dialog.asked == []
    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.saved_address == "https://jira.example.com"
    assert store.get(JIRA_PAT) == TOKEN
    assert dialog.token_edit.text() == ""
    text = settings_file(tmp_path).read_text(encoding="utf-8")
    assert 'base_url = "https://jira.example.com"' in text and TOKEN not in text


def test_saving_untested_asks_for_confirmation(qtbot, tmp_path) -> None:
    store = InMemorySecretStore()
    declined = make(qtbot, tmp_path, store=store, answers=(False,))
    fill(declined)
    declined.save_button.click()
    assert len(declined.asked) == 1
    assert store.get(JIRA_PAT) is None and not settings_file(tmp_path).exists()
    assert declined.isVisible()
    declined.confirm_again = None
    accepted = make(qtbot, tmp_path, store=store, answers=(True,))
    fill(accepted)
    accepted.save_button.click()
    assert store.get(JIRA_PAT) == TOKEN and settings_file(tmp_path).exists()


def test_empty_token_field_keeps_the_stored_token(qtbot, tmp_path) -> None:
    store = InMemorySecretStore()
    store.set(JIRA_PAT, "stored-token-0123456789")
    dialog = make(qtbot, tmp_path, store=store)
    fill(dialog, "https://new.example.com", token="")
    dialog.save_button.click()
    assert store.get(JIRA_PAT) == "stored-token-0123456789"
    assert 'base_url = "https://new.example.com"' in settings_file(tmp_path).read_text("utf-8")


def test_cancel_changes_nothing(qtbot, tmp_path) -> None:
    store = InMemorySecretStore()
    dialog = make(qtbot, tmp_path, store=store)
    fill(dialog)
    dialog.cancel_button.click()
    assert dialog.result() == dialog.DialogCode.Rejected
    assert store.get(JIRA_PAT) is None and not settings_file(tmp_path).exists()
    assert dialog.token_edit.text() == "" and dialog.saved_address is None


def test_write_failure_keeps_dialog_open_and_shows_the_reason(qtbot, tmp_path) -> None:
    dialog = make(qtbot, tmp_path)
    settings_file(tmp_path).write_text("[jira\nbroken", encoding="utf-8")
    fill(dialog)
    dialog.save_button.click()
    assert dialog.isVisible() and dialog.saved_address is None
    assert "not valid TOML" in dialog.status_label.text()
    assert settings_file(tmp_path).read_text(encoding="utf-8") == "[jira\nbroken"


def test_environment_override_blocks_saving(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_BASE_URL, "https://from-env.example.com")
    dialog = make(qtbot, tmp_path)
    fill(dialog)
    assert dialog.status_label.text() == ENV_OVERRIDE_NOTE
    assert not dialog.save_button.isEnabled()


def test_token_never_logged(qtbot, tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    dialog = make(qtbot, tmp_path)
    fill(dialog)
    dialog.test_button.click()
    qtbot.waitUntil(lambda: "Connected" in dialog.status_label.text(), timeout=5000)
    dialog.save_button.click()
    assert TOKEN not in caplog.text
    assert "Jira token stored" in caplog.text
