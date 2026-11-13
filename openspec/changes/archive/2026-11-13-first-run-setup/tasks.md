# Tasks

## 1. Address and settings file

- [x] 1.1 Implement `validate_address` and `local_settings_path` in `config/local_settings.py`; verify tests for a valid address with trailing slash, http, missing host, user and password (reason must not echo the secret), query and path, the placeholder host and empty text
- [x] 1.2 Implement `set_base_url` with a line-level edit, file creation, a new `[jira]` table when absent, re-parse verification and atomic replace; verify tests that other settings and comments survive, a missing file is created, an inline-table or duplicate-key file is rejected untouched, and a failing write leaves the old file intact

## 2. Connection test

- [x] 2.1 Add `JiraHttp.get_myself()` (GET `/rest/api/2/myself`, through the existing choke point); verify a test that it uses GET and the exact path and that the GET-only guarantee test still passes
- [x] 2.2 Implement `test_connection` with plain-language results for success (display name), `auth`, `tls`, `connection`, `timeout` and other errors, registering the token with the redactor; verify tests with `httpx.MockTransport` for each outcome and that the token never appears in messages or captured logs

## 3. Dialog

- [x] 3.1 Implement `SetupDialog` (address, masked token, status label, Test connection on a background runnable, Save, Cancel) with injected collaborators, Save enabled only for a valid address and an available token, confirmation when saving untested, and the environment-override block; verify headless tests for first run, opened later showing "token stored", cancel changing nothing, validation messages, a successful and a failed test keeping the dialog responsive, keeping the stored token when the field is empty, and clearing the token field afterwards
- [x] 3.2 Make Save store the token, write the address, and report failures without closing; verify tests that the secret store receives the token, no file or log contains it, a write failure keeps the dialog open with the reason, and Cancel writes nothing

## 4. Window integration

- [x] 4.1 Add `MainWindow.set_service` and the "Jira setup…" action, the "Set up Jira…" button on the not-configured page, the automatic prompt after the window is shown when the address is a placeholder or the token is missing, and deferral of the swap while a refresh runs; verify window tests for the automatic prompt, a cancelled prompt leaving the message page, swapping the service starting a refresh and clearing old data, and the deferred swap
- [x] 4.2 Add the `reconfigure` factory in `ui/app.py` (reload settings, build and close clients) and wire it to the dialog result; verify tests that a saved address and token lead to a working refresh through a fake transport without restart

## 5. Docs and checks

- [x] 5.1 Update `docs/security.md` (the dialog as the normal way, the one-liner as an alternative, what is and is not stored where), `docs/configuration.md` (the local file and the environment override) and `docs/dashboard.md`; verify the text matches the behaviour
- [x] 5.2 Run the real application against a temporary settings file and the real Jira with the stored token kept untouched (test connection only), confirm the messages for a good and a deliberately wrong address, then verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass
