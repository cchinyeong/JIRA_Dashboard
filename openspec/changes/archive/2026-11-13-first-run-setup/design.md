# Design

## Context

Settings load from `default.toml`, then the local file (`JIRA_DASHBOARD_CONFIG_FILE` or `./settings.local.toml`), then `JIRA_DASHBOARD_*` environment variables. `Settings` is frozen. The token lives in Credential Manager via `services/secrets.py` (`get_secret`/`set_secret`, keyring-backed, registered with the log redactor). `ui/app.launch()` builds the client and service once from the settings; a placeholder address gives an `_UnconfiguredClient` and a "not configured" message page. `JiraHttp` is GET-only with a single choke point `_get_once`, and already classifies errors (`auth`, `timeout`, `connection`, `tls`, `http`).

## Goals / Non-Goals

**Goals:**
- Configure address and token from inside the app, safely, and use them immediately.
- Keep every existing security rule: token only in Credential Manager, never in files or logs, GET only.

**Non-Goals:**
- Proxies, multiple profiles, expiry reminders, other settings in the UI, write credentials.

## Decisions

- **Dialog** (`ui/setup_dialog.py`, `QDialog`): address `QLineEdit`, token `QLineEdit` with `Password` echo mode and no clipboard history hint, a status label, buttons Test connection / Save / Cancel. It receives its collaborators (`secret_store`, `tester`, `settings_writer`, current settings) so tests use fakes. Token text lives only in the line edit; on accept or reject the edit is cleared and the dialog never returns the token to the caller.
- **Address validation** is a pure function `validate_address(text) -> (clean | None, reason | None)` in `config/local_settings.py` using `urllib.parse`: scheme `https`, hostname present, no username/password, no query/fragment, path empty or `/`; rejects the placeholder host; strips the trailing slash. Reasons never include the credential part.
- **Connection test** (`services/connection_test.py`): `test_connection(address, token, transport=None) -> TestResult(ok, kind, message, user)`. It builds a temporary `Settings` copy with the entered address (via `model_copy`), a `JiraHttp` with the entered token, calls the new `JiraHttp.get_myself()` (`GET /rest/api/2/myself`) and maps `JiraApiError.kind` to plain messages (`auth` → "token rejected; check it has not expired", `tls` → certificate problem, `connection`/`timeout` → unreachable). The token is registered with the redactor before use. A `QRunnable` runs it so the dialog stays responsive; late results after close are ignored. When the token field is empty the stored token is read inside the worker.
- **Writing the address** (`config/local_settings.py: set_base_url(path, address)`): a line-level edit that changes only the `base_url` line inside the `[jira]` table, adds the line (or the table) when absent, and creates the file when missing. The new text is parsed with `tomllib` and checked to contain the expected address before an atomic `os.replace` of a temp file in the same folder; on any failure the old file is untouched and the error is shown. No TOML-writing dependency is added; comments and other settings survive. The path follows the same rule as the loader, exposed as `local_settings_path()` so both agree.
- **Environment override:** if `JIRA_DASHBOARD_JIRA__BASE_URL` is set, it wins over the file. The dialog shows a note and the saved value would be ignored, so Save is blocked with an explanation rather than silently having no effect.
- **Applying without restart:** `MainWindow` gets `set_service(service, not_configured)`, which swaps the service, resets the table, filters' data, banner and selection, and starts a refresh. `ui/app.py` provides a `reconfigure()` factory that reloads settings (`get_settings()`), builds the client (`JiraOnPremClient` closed on replacement) and service, and is passed to the window as a callback. After Save, the dialog closes, the callback runs, then the window refreshes.
- **Automatic prompt:** at start, if the address is the placeholder or `get_secret` raises `MissingSecretError`, the window opens the dialog once the window is shown (`QTimer.singleShot(0, …)`), not before, so the user sees the application behind it. The not-configured message page remains for cancelled dialogs, with a "Set up Jira…" button on it. A `no_token` refresh result shows the same page and offers the dialog.
- **Toolbar action** "Jira setup…" always available (also while busy, but Save applies after the running refresh finishes, by deferring the swap until `_busy` clears).
- **Redaction and logging:** only non-secret facts are logged ("Jira address updated", the host, "token stored"); a test asserts that neither the token nor the full Authorization header appears in captured logs.
- **Testing:** dialog tests (pytest-qt) with a fake tester, `InMemorySecretStore` and `tmp_path` settings file; connection-test tests with `httpx.MockTransport` for 200, 401, 403, timeout, TLS-like and connection errors, asserting GET only and the exact path; local-settings tests for create, update with comments and other tables preserved, atomic failure, validation table; window tests for the automatic prompt and for `set_service`. No test touches Credential Manager or the network.

## Risks / Trade-offs

- [Line-level TOML editing could mis-handle unusual files] → the result is re-parsed and verified before replacing, and the previous file stays on any mismatch; the unusual cases (inline table `jira = {…}`, duplicate keys) are rejected with a clear message instead of guessed.
- [Token typed into a Qt field lives in memory briefly] → cleared on close; not logged; unavoidable for any input field.
- [`/rest/api/2/myself` might be blocked by a proxy] → failures are reported with their kind; Save without a successful test remains possible after confirmation.
- [Swapping the service while a refresh runs] → deferred until the running refresh finishes.
- [The settings file sits in a OneDrive folder] → documented; the file holds only the address, never the token.
