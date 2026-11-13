import logging
import os
from typing import Protocol

import keyring
from keyring.errors import PasswordDeleteError
from pydantic import SecretStr

from jira_dashboard.utils.redaction import register_secret

SERVICE_NAME = "jira-dashboard"
JIRA_PAT = "jira-pat"
ALLOW_ENV_VAR = "JIRA_DASHBOARD_ALLOW_ENV_SECRETS"
ENV_PREFIX = "JIRA_DASHBOARD_SECRET_"

logger = logging.getLogger(__name__)


class MissingSecretError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Secret {name!r} is not stored. Store it with "
            f"jira_dashboard.services.secrets.set_secret({name!r}, ...)."
        )
        self.name = name


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class InMemorySecretStore:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self._data.get(name)

    def set(self, name: str, value: str) -> None:
        self._data[name] = value

    def delete(self, name: str) -> None:
        self._data.pop(name, None)


class KeyringSecretStore:
    def __init__(self, service: str = SERVICE_NAME) -> None:
        self._service = service

    def get(self, name: str) -> str | None:
        return keyring.get_password(self._service, name)

    def set(self, name: str, value: str) -> None:
        keyring.set_password(self._service, name, value)

    def delete(self, name: str) -> None:
        try:
            keyring.delete_password(self._service, name)
        except PasswordDeleteError:
            pass


def _env_name(name: str) -> str:
    return ENV_PREFIX + name.upper().replace("-", "_")


def get_secret(name: str, store: SecretStore | None = None) -> SecretStr:
    value = (store or KeyringSecretStore()).get(name)
    if value is None and os.environ.get(ALLOW_ENV_VAR) == "1":
        value = os.environ.get(_env_name(name))
        if value is not None:
            logger.warning("Secret %r read from environment (development only)", name)
    if not value:
        raise MissingSecretError(name)
    register_secret(value)
    return SecretStr(value)


def set_secret(name: str, value: str, store: SecretStore | None = None) -> None:
    (store or KeyringSecretStore()).set(name, value)
    register_secret(value)


def delete_secret(name: str, store: SecretStore | None = None) -> None:
    (store or KeyringSecretStore()).delete(name)
