# Design

## Context

The `logging` section (level, directory) already exists in settings (archived `app-config`), and `keyring` is installed. `jira_dashboard.utils` and `jira_dashboard.services` are empty packages. The Jira client, built next, will need a PAT and will log requests. Windows Credential Manager (DPAPI, per user) was chosen during exploration.

## Goals / Non-Goals

**Goals:**
- Safe-by-default logging: a secret cannot reach a log through normal use.
- A small `SecretStore` abstraction the Jira client and later integrations can share.

**Non-Goals:**
- Authentication logic, HTTP, audit trail, OAuth/Graph secrets, structured/JSON logging.

## Decisions

- **Logging in `utils/logging.py`**: `configure_logging(settings.logging)` attaches a `StreamHandler` and a `RotatingFileHandler` (1 MB, 5 backups, UTF-8) to the root logger, writing `dashboard.log` in the configured directory (created if missing). It removes handlers it previously installed first, so repeated calls are idempotent. Rotation size and backups are constants for now, not settings.
- **Redaction as a `logging.Filter` on each handler**, not on loggers, so records from every library are covered. The filter formats `record.getMessage()` (resolving args), applies the redaction, then clears `args`. Exception text is redacted by a formatter subclass that scrubs the final formatted output including the traceback. Alternative: redact only at the logger level; rejected because it misses third-party loggers and tracebacks.
- **Redaction rules:** regexes for `Bearer <token>`, `Basic <token>`, `Authorization:` values and `token|password|secret|apikey` key-value pairs, plus exact-match masking of values in a thread-safe registry (`register_secret`). Output replaces matches with `***`. Registry entries shorter than 4 characters are ignored to avoid masking ordinary text.
- **`SecretStore` protocol in `services/secrets.py`** with `get`, `set`, `delete`; implementations `KeyringSecretStore` (service name `jira-dashboard`) and `InMemorySecretStore` (tests). `get_secret(name)` returns `SecretStr`, registers it for redaction and raises `MissingSecretError` when absent. Alternative: expose raw `keyring` calls; rejected so tests and later vaults can swap the backend.
- **Environment fallback** `JIRA_DASHBOARD_SECRET_<NAME>` only when `JIRA_DASHBOARD_ALLOW_ENV_SECRETS=1`; keyring wins when both exist. It is documented as development only and logged as a warning when used.
- **PAT name constant** `JIRA_PAT = "jira-pat"`; PAT guidance goes in `docs/security.md`: a dedicated read-only account where possible, an expiry, and rotation.
- **Tests** use the in-memory store and a fake keyring backend; no real Credential Manager writes in unit tests. A single opt-in integration test (skipped by default) covers the real backend.

## Risks / Trade-offs

- [Regex redaction can miss unusual formats] → Exact-value registry is the primary defence; regexes are a second layer.
- [Over-masking short values] → Minimum registry length of 4.
- [Windows Credential Manager is Windows-only and per-user] → Matches the target platform; the protocol allows another backend (for example a vault) later.
- [Env fallback could be left on] → Disabled by default and warned at use.
