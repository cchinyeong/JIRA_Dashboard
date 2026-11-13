# Proposal

## Why

Today a new user must edit `settings.local.toml` by hand and run a Python one-liner to store the Jira token before the dashboard shows anything. The window only tells them what to do. That is the last gap in MVP-1: a user should be able to install, start the application and be guided to a working connection without leaving it. The token must still never touch a file, and the application must stay read-only toward Jira.

## What Changes

- A **Jira setup dialog**, opened automatically when the Jira address is still the placeholder or no token is stored, and any time from a "Jira setup…" toolbar action (to rotate the token or change the address).
- Fields: Jira address (validated: `https` only, a host, no credentials in it, no path/query), and a masked Personal Access Token field. The token is never shown, never logged and never written to a file; it goes to Windows Credential Manager through the existing secret store. An already stored token is shown only as "stored", and leaving the field empty keeps it.
- A **Test connection** button that makes one read-only request with the entered values on a background thread, and reports in plain words: connected as <display name>, address unreachable, certificate problem, token rejected, or other. Saving is allowed only after a successful test, or explicitly without a test.
- **Save** writes the address into the local settings file (`settings.local.toml`, same location rule as the loader), changing only `jira.base_url` and keeping the rest of the file, via a temporary file and atomic replace; the token is stored in Credential Manager. The window then applies the new settings **without a restart**, and starts a refresh.
- One new read-only call, `JiraHttp.get_myself()` (`GET /rest/api/2/myself`), used only by the test. The GET-only guarantee stays.
- Cancel changes nothing.

## Capabilities

### New Capabilities
- `first-run-setup`: the setup dialog, address validation, connection test, secure saving of address and token, applying them without restart.

### Modified Capabilities
- `dashboard-window`: "Jira not configured" now opens the setup dialog instead of only showing a message, and a "Jira setup…" action exists.

## Impact

- Code: new `ui/setup_dialog.py`, `config/local_settings.py` (safe read/update of the local file's `jira.base_url`), `services/connection_test.py`; `jira_http.py` gains `get_myself`; `ui/main_window.py` and `ui/app.py` gain the action, the automatic prompt and re-configuration (replace the service and client).
- Tests: headless dialog tests with a fake connection tester and an in-memory secret store; file-update tests in `tmp_path`; connection-test tests with `httpx.MockTransport`. No test touches the real Credential Manager or the network.
- Docs: `docs/security.md` (the dialog replaces the one-liner, which stays as an alternative), `docs/configuration.md`, `docs/dashboard.md`.
- Out of scope: proxy settings, several Jira profiles, token expiry reminders, write-capable credentials (MVP-4), changing other settings from the UI, Jira Cloud sign-in (MVP-9).
