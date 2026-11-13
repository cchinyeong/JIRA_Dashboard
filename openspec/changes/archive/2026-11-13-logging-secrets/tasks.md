# Tasks

## 1. Redaction

- [x] 1.1 Add redaction rules and a thread-safe secret registry (`register_secret`, minimum length 4) in `utils/redaction.py`; verify unit tests for Bearer, Basic, `Authorization`, key-value pairs and registered values
- [x] 1.2 Add a redacting logging filter and formatter (message, args and traceback); verify tests that a registered secret in an argument and in an exception traceback never appears in output

## 2. Logging setup

- [x] 2.1 Implement `configure_logging` in `utils/logging.py` (console plus rotating file, level from settings, log directory created, idempotent); verify tests for level, file creation, rotation bounds and double setup
- [x] 2.2 Export the public logging names; verify `from jira_dashboard.utils.logging import configure_logging` works in a test

## 3. Credential storage

- [x] 3.1 Add `SecretStore` protocol, `InMemorySecretStore`, `KeyringSecretStore` and `MissingSecretError` in `services/secrets.py`; verify tests with the in-memory store and a fake keyring backend for round trip, deletion and missing secret
- [x] 3.2 Add `get_secret`, `set_secret` and `delete_secret` returning `SecretStr`, registering retrieved values for redaction, and the opt-in env fallback; verify tests for masked repr, explicit reveal, fallback disabled by default, fallback enabled, keyring precedence and redaction after retrieval
- [x] 3.3 Add a skipped-by-default integration test against the real Credential Manager; verify it is collected and skipped without the opt-in flag

## 4. Docs and quality

- [x] 4.1 Write `docs/security.md` covering PAT creation, storing and rotating via Credential Manager, the dev-only fallback and log redaction limits; verify the commands in it run as written
- [x] 4.2 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass
