# Tasks

## 1. Qt setup

- [x] 1.1 Add `PySide6-Essentials` and dev dependency `pytest-qt`, set `QT_QPA_PLATFORM=offscreen` in `tests/conftest.py`, and add a `ui` package with an `__init__.py`; verify `uv sync` succeeds on Python 3.15 and a pytest-qt test creates a `QApplication` and a visible-state widget offscreen
- [x] 1.2 Update the package layout test to include `ui` and keep the "no premature folders" check for `skills`, `agents`, `workflows` and `database`; verify `uv run pytest tests/unit/test_package.py` passes

## 2. Table model

- [x] 2.1 Implement `TicketTableModel` with the twelve columns, display text rules (dates, days, unknown text, "Unknown (raw)" status), read-only flags, finding count, tint and tooltip, and unknown styling; verify headless tests for known values, unknown values, the non-standard status, a ticket with and without findings, and that cells are not editable
- [x] 2.2 Implement the sorting proxy (`SortRole`, default order by numeric key, unknown always last in both directions); verify tests for CAE-99 before CAE-100, ascending and descending by assignee with unknown last, and sorting by remaining effort and target end

## 3. Window and refresh

- [x] 3.1 Implement the refresh worker (runnable on the thread pool, signal with the `RefreshResult`); verify a pytest-qt test that a refresh runs off the interface thread and delivers its result
- [x] 3.2 Implement `MainWindow` with the table, toolbar Refresh button and F5, busy indication, status bar summary, and failure and warning banner; verify tests with a fake service for refresh disabling the button while running and re-enabling it, the table showing new data, a failed refresh keeping the previous rows and showing the message, a warning being shown, the banner clearing after success, and the status bar counts
- [x] 3.3 Implement the not-configured state (placeholder address and `no_token`) with an explanatory message, refresh disabled for the placeholder address and left available for `no_token` so the user can retry after storing the token; verify tests for both cases showing the setting name or the token instruction and no table data
- [x] 3.4 Implement "Open in Jira" (toolbar, context menu, double-click) through an injectable opener using only `ticket_link`; verify tests for an allowed link being opened, a refused link opening nothing with the action disabled, and no selection disabling the action

## 4. Application and docs

- [x] 4.1 Implement `ui.app.run()` (settings, client, service, window, automatic first refresh) and make `jira_dashboard.main()` launch it; verify tests that the window is shown before a blocked refresh completes and that the placeholder-address start works, updating the old `main` test
- [x] 4.2 Write `docs/dashboard.md` and update `README.md` (how to start, what the columns mean, refresh and failure behaviour, recommending `UV_PROJECT_ENVIRONMENT` outside OneDrive); verify the documented commands run as written
- [x] 4.3 Start the real application once against the real Jira, confirm the table, sorting, findings tint, refresh and "Open in Jira" by hand or with a screenshot, then verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass

## Workflow follow-up

- Next MVP-1 changes: details panel; filter bar and grouped view; first-run setup dialog for the Jira address and token.
