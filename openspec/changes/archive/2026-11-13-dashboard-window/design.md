# Design

## Context

The `TicketService` (see `ticket-service`) gives the window everything it needs: `refresh()` returning a `RefreshResult`, an immutable `snapshot`, `list_tickets`, `summary`, and `ticket_link`. Refresh takes about 7 s against the real Jira (353 tickets), so it must not run on the UI thread. The entry point `jira-dashboard` maps to `jira_dashboard:main`, currently a print stub. The target platform is Windows; the project runs on Python 3.15 where `PySide6-Essentials` 6.12 resolves (the full `PySide6` would also pull web-engine and PDF packages that are not needed). The virtual environment lives inside OneDrive.

## Goals / Non-Goals

**Goals:**
- A first window that is useful on its own: see all tickets, sort, refresh, open in Jira, notice problems.
- UI code thin enough that all logic stays in the service and is tested headlessly.

**Non-Goals:**
- Details panel, filter bar, grouped view, first-run dialog, theming, packaging, any editing.

## Decisions

- **Toolkit: PySide6 (Qt Widgets)** via the `PySide6-Essentials` package only. Alternative: full `PySide6`; rejected for size (web engine). Alternative: Tkinter; rejected earlier for weak table support.
- **Package `jira_dashboard.ui`:** `app.py` (bootstrap: settings, secrets, client, service, window, `run()` returning an exit code), `main_window.py`, `ticket_model.py` (a `QAbstractTableModel`), `refresh_worker.py`. `jira_dashboard.main()` imports `ui.app` lazily and returns its exit code, so importing the package does not require Qt.
- **Model/view:** `TicketTableModel` holds the current `list[Ticket]` and exposes `DisplayRole`, `ToolTipRole`, `BackgroundRole` (finding tint), `FontRole`/`ForegroundRole` (unknown style: italic grey) and a `SortRole` with `(is_unknown, value)` tuples. A `QSortFilterProxyModel` subclass sorts on `SortRole`; unknown always sorts last by inverting for descending order. The proxy is also where the filter bar will plug in later. Read-only: no `ItemIsEditable` flag.
- **Display rules:** dates as `dd MMM yyyy`; remaining effort with up to one decimal, in days; status shows `Unknown (<raw>)` for the unknown status; Findings shows the count or nothing.
- **Refresh worker:** a `QRunnable` run on `QThreadPool` that calls `service.refresh()` and emits a `finished(RefreshResult)` signal through a small `QObject`. Alternative: a `QThread` with a worker object; equivalent, but the pool needs less lifecycle code. The window sets a `refreshing` state, disables the button and F5 shortcut and shows an indeterminate progress bar. A `busy` result (impossible from the UI but possible in principle) is ignored quietly.
- **Failure banner:** a dismissible `QLabel` panel above the table, red for `failed`, amber for warnings; hidden on a successful refresh without warnings. The table keeps its data because the service keeps the snapshot.
- **Not configured:** `app.run()` builds the client lazily: if `settings.jira.is_placeholder`, the window starts in a "not configured" state (a centered message naming `jira.base_url`, `settings.local.toml` and `docs/security.md`) and refresh is disabled. If the first refresh returns `no_token`, the same panel shows the token instructions. A later change replaces the panel with a setup dialog.
- **Open in Jira:** `QDesktopServices.openUrl(QUrl(link))` behind an injectable `opener` callable so tests can capture it. The link comes only from `service.ticket_link(ticket)`.
- **Status bar:** a permanent widget with `n tickets · refreshed HH:MM · u unreadable · f with findings`.
- **Testing:** `pytest-qt` with `QT_QPA_PLATFORM=offscreen`, set in `tests/conftest.py` before any Qt import. A `FakeService` stands in for the real one (scripted results, optional blocking via an event) so window tests are deterministic. The model is tested without a window.
- **Environment:** because the `.venv` is inside OneDrive and Qt adds many files, the docs recommend `UV_PROJECT_ENVIRONMENT` pointing at a folder outside OneDrive (for example under `%LOCALAPPDATA%`), and the install is verified once on this machine.

## Risks / Trade-offs

- [Qt wheels on Python 3.15 are new] → `PySide6-Essentials` 6.12 resolves for 3.15 on Windows; the install and an offscreen test run are part of the first task, before any UI code.
- [Offscreen tests do not catch visual problems] → A manual check of the real window against the real Jira is a task.
- [OneDrive syncing the virtual environment (stale files, locked folders seen earlier)] → Recommend moving the environment out of OneDrive; documented, not forced.
- [Sorting with unknown-last in both directions is unusual] → Implemented in one proxy method with direct tests.
- [Large tables] → About 350 rows today; the model is a plain list, so thousands remain fine.
- [A refresh finishing after the window closes] → The worker holds no widget references; the window ignores late results once closed.
