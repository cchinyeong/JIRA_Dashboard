# Proposal

## Why

MVP-0 requires working logging and externalised secrets. The Jira on-prem client (next change) needs a Personal Access Token, and exploration settled on Windows Credential Manager. Logs must never leak that token, because ticket data and HTTP headers will pass through the app.

## What Changes

- Add logging setup driven by the existing `logging` settings (level, directory): console plus a rotating log file, with a consistent format.
- Add a redaction filter that masks credential-like values (Bearer/Basic tokens, `Authorization` headers, `token=`/`password=` pairs, and any registered secret value) in log messages and arguments.
- Add a `SecretStore` interface with a Windows Credential Manager implementation (via `keyring`) and an in-memory implementation for tests.
- Secrets are returned as `pydantic.SecretStr` so they do not appear in `repr`, `str` or logs.
- Add a development-only environment-variable fallback (`JIRA_DASHBOARD_SECRET_<NAME>`), documented as not for production.
- Provide `get_secret` / `set_secret` / `delete_secret` for the Jira PAT, namespaced under one service name.

## Capabilities

### New Capabilities
- `application-logging`: Configured, rotating, redacted application logging.
- `credential-storage`: Storing and retrieving credentials outside source code and settings, with safe handling in memory and in logs.

### Modified Capabilities

## Impact

- Code: `src/jira_dashboard/utils/logging.py`, `src/jira_dashboard/services/secrets.py`, tests in `tests/unit/`.
- Dependencies: none new (`keyring` already added).
- Docs: `docs/security.md` (PAT creation, storage and rotation guidance).
- Out of scope: Jira authentication logic and HTTP calls (`jira-client-interface`), Microsoft Graph/OAuth secrets (MVP-6), audit logging (later MVP).
