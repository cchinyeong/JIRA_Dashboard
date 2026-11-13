import logging
import os
from collections.abc import Callable
from pathlib import Path

from pydantic import SecretStr
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jira_dashboard.config import Settings
from jira_dashboard.config.local_settings import (
    ENV_BASE_URL,
    LocalSettingsError,
    local_settings_path,
    set_base_url,
    validate_address,
)
from jira_dashboard.services.connection_test import ConnectionResult, check_connection
from jira_dashboard.services.secrets import (
    JIRA_PAT,
    KeyringSecretStore,
    MissingSecretError,
    SecretStore,
    get_secret,
    set_secret,
)

logger = logging.getLogger(__name__)

Tester = Callable[[Settings, str, SecretStr], ConnectionResult]
Confirm = Callable[[str], bool]

TOKEN_STORED_HINT = "A token is stored. Leave this empty to keep it."
TOKEN_MISSING_HINT = "Paste a Jira Personal Access Token."
ENV_OVERRIDE_NOTE = (
    "The address is set by the environment variable JIRA_DASHBOARD_JIRA__BASE_URL, which "
    "overrides the settings file. Remove the variable to change it here."
)


def ask_yes_no(text: str) -> bool:
    answer = QMessageBox.question(None, "Jira setup", text)
    return answer == QMessageBox.StandardButton.Yes


class _Signals(QObject):
    finished = Signal(int, object)


class _TestWorker(QRunnable):
    def __init__(
        self,
        serial: int,
        settings: Settings,
        address: str,
        typed: str,
        store: SecretStore,
        tester: Tester,
    ) -> None:
        super().__init__()
        self.signals = _Signals()
        self._args = (serial, settings, address, typed, store, tester)

    def run(self) -> None:
        serial, settings, address, typed, store, tester = self._args
        try:
            token = SecretStr(typed) if typed else get_secret(JIRA_PAT, store)
            result = tester(settings, address, token)
        except MissingSecretError:
            result = ConnectionResult(False, "other", "Enter a token first.")
        except Exception:
            logger.exception("Connection test worker failed")
            result = ConnectionResult(False, "other", "The test failed unexpectedly.")
        self.signals.finished.emit(serial, result)


class SetupDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        *,
        secret_store: SecretStore | None = None,
        tester: Tester = check_connection,
        settings_path: Path | None = None,
        confirm: Confirm = ask_yes_no,
        pool: QThreadPool | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jira setup")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._settings = settings
        self._store = secret_store or KeyringSecretStore()
        self._tester = tester
        self._path = settings_path or local_settings_path()
        self._confirm = confirm
        self._pool = pool or QThreadPool.globalInstance()
        self._serial = 0
        self._tested_ok = False
        self._testing = False
        self._token_stored = bool(self._store.get(JIRA_PAT))
        self._env_override = bool(os.environ.get(ENV_BASE_URL))
        self.saved_address: str | None = None

        self.address_edit = QLineEdit()
        if not settings.jira.is_placeholder:
            self.address_edit.setText(settings.jira.base_url)
        self.address_edit.setPlaceholderText("https://jira.example.com")
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(
            TOKEN_STORED_HINT if self._token_stored else TOKEN_MISSING_HINT
        )
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.test_button = QPushButton("Test connection")
        self.test_button.clicked.connect(self.start_test)
        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)

        form = QFormLayout()
        form.addRow("Jira address:", self.address_edit)
        form.addRow("Token:", self.token_edit)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.test_button)
        layout.addWidget(self.status_label)
        layout.addWidget(buttons)

        self.address_edit.textChanged.connect(self._inputs_changed)
        self.token_edit.textChanged.connect(self._inputs_changed)
        self._inputs_changed()

    @property
    def address(self) -> str | None:
        return validate_address(self.address_edit.text())[0]

    def _token_available(self) -> bool:
        return bool(self.token_edit.text()) or self._token_stored

    def _show(self, text: str) -> None:
        self.status_label.setText(text)

    def _inputs_changed(self, *_args) -> None:
        self._tested_ok = False
        self._serial += 1
        _clean, reason = validate_address(self.address_edit.text())
        text = self.address_edit.text().strip()
        if self._env_override:
            self._show(ENV_OVERRIDE_NOTE)
        elif text and reason:
            self._show(reason)
        else:
            self._show("")
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        valid = self.address is not None and not self._env_override
        ready = valid and self._token_available() and not self._testing
        self.test_button.setEnabled(ready)
        self.save_button.setEnabled(ready)

    def start_test(self) -> None:
        address = self.address
        if address is None or not self._token_available() or self._testing:
            return
        self._testing = True
        self._show("Testing the connection…")
        self._refresh_buttons()
        worker = _TestWorker(
            self._serial,
            self._settings,
            address,
            self.token_edit.text(),
            self._store,
            self._tester,
        )
        worker.signals.finished.connect(self._on_test_finished)
        self._pool.start(worker)

    def _on_test_finished(self, serial: int, result: ConnectionResult) -> None:
        self._testing = False
        if serial == self._serial:
            self._tested_ok = result.ok
            self._show(result.message)
        self._refresh_buttons()

    def save(self) -> None:
        address = self.address
        if address is None or not self._token_available() or self._env_override:
            return
        if not self._tested_ok and not self._confirm(
            "The connection has not been tested successfully. Save anyway?"
        ):
            return
        typed = self.token_edit.text()
        try:
            if typed:
                set_secret(JIRA_PAT, typed, self._store)
                logger.info("Jira token stored")
            set_base_url(self._path, address)
            logger.info("Jira address updated to %s", address)
        except LocalSettingsError as exc:
            self._show(f"The address could not be saved: {exc}")
            return
        except Exception as exc:
            logger.exception("Saving the Jira setup failed")
            self._show(f"The setup could not be saved ({type(exc).__name__}). See the log.")
            return
        self.token_edit.clear()
        self.saved_address = address
        self.accept()

    def done(self, result: int) -> None:
        self._serial += 1
        self.token_edit.clear()
        super().done(result)
