import os
import uuid

import pytest

from jira_dashboard.services.secrets import (
    KeyringSecretStore,
    MissingSecretError,
    delete_secret,
    get_secret,
    set_secret,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("JIRA_DASHBOARD_TEST_KEYRING") != "1",
    reason="set JIRA_DASHBOARD_TEST_KEYRING=1 to use the real Credential Manager",
)


def test_real_credential_manager_round_trip() -> None:
    name = f"test-{uuid.uuid4().hex}"
    store = KeyringSecretStore()
    try:
        set_secret(name, "integration-value-1", store)
        assert get_secret(name, store).get_secret_value() == "integration-value-1"
    finally:
        delete_secret(name, store)
    with pytest.raises(MissingSecretError):
        get_secret(name, store)
