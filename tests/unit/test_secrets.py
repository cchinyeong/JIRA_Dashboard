import logging

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

from jira_dashboard.services.secrets import (
    ALLOW_ENV_VAR,
    InMemorySecretStore,
    KeyringSecretStore,
    MissingSecretError,
    delete_secret,
    get_secret,
    set_secret,
)
from jira_dashboard.utils.redaction import clear_secrets, redact


class FakeKeyring(KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        self.data: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.data.get((service, username))

    def set_password(self, service, username, password):
        self.data[(service, username)] = password

    def delete_password(self, service, username):
        if (service, username) not in self.data:
            raise PasswordDeleteError("missing")
        del self.data[(service, username)]


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch):
    clear_secrets()
    monkeypatch.delenv(ALLOW_ENV_VAR, raising=False)
    original = keyring.get_keyring()
    keyring.set_keyring(FakeKeyring())
    yield
    keyring.set_keyring(original)
    clear_secrets()


def test_round_trip_and_delete() -> None:
    store = KeyringSecretStore()
    set_secret("jira-pat", "value-12345", store)
    assert get_secret("jira-pat", store).get_secret_value() == "value-12345"
    delete_secret("jira-pat", store)
    with pytest.raises(MissingSecretError, match="jira-pat"):
        get_secret("jira-pat", store)


def test_delete_missing_is_harmless() -> None:
    delete_secret("never-stored", KeyringSecretStore())


def test_secret_is_masked_when_printed() -> None:
    store = InMemorySecretStore()
    store.set("jira-pat", "value-12345")
    secret = get_secret("jira-pat", store)
    assert "value-12345" not in str(secret)
    assert "value-12345" not in repr(secret)
    assert secret.get_secret_value() == "value-12345"


def test_missing_secret_raises() -> None:
    with pytest.raises(MissingSecretError):
        get_secret("absent", InMemorySecretStore())


def test_empty_secret_treated_as_missing() -> None:
    store = InMemorySecretStore()
    store.set("empty", "")
    with pytest.raises(MissingSecretError):
        get_secret("empty", store)


def test_env_fallback_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_DASHBOARD_SECRET_JIRA_PAT", "env-value-1")
    with pytest.raises(MissingSecretError):
        get_secret("jira-pat", InMemorySecretStore())


def test_env_fallback_enabled(monkeypatch, caplog) -> None:
    monkeypatch.setenv(ALLOW_ENV_VAR, "1")
    monkeypatch.setenv("JIRA_DASHBOARD_SECRET_JIRA_PAT", "env-value-1")
    with caplog.at_level(logging.WARNING):
        value = get_secret("jira-pat", InMemorySecretStore())
    assert value.get_secret_value() == "env-value-1"
    assert "development only" in caplog.text


def test_store_wins_over_env(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_ENV_VAR, "1")
    monkeypatch.setenv("JIRA_DASHBOARD_SECRET_JIRA_PAT", "env-value-1")
    store = InMemorySecretStore()
    store.set("jira-pat", "stored-value-1")
    assert get_secret("jira-pat", store).get_secret_value() == "stored-value-1"


def test_retrieved_secret_is_redacted() -> None:
    store = InMemorySecretStore()
    store.set("jira-pat", "redact-me-12345")
    get_secret("jira-pat", store)
    assert "redact-me-12345" not in redact("leak redact-me-12345")


def test_storing_creates_no_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    set_secret("jira-pat", "value-12345", KeyringSecretStore())
    assert list(tmp_path.iterdir()) == []
