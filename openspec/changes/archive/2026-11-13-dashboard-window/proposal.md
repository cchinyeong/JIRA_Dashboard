# Proposal

## Why

MVP-1 is "see VE Jira workload in one place". Everything behind the window now exists and works against the real Jira (client, mapper, findings, ticket service), but there is still no window: `jira-dashboard` just prints its name. This change delivers the first usable screen: the application window with a sortable ticket table, a refresh that keeps the interface responsive, "Open in Jira", and a visible indicator of data-quality findings. Details panel, filters and first-run setup follow as separate small changes.

## What Changes

- `jira-dashboard` now starts a PySide6 window and refreshes automatically on start.
- A ticket table with columns Key, Summary, Type, Status, Priority, Assignee, Domain, Sprint, Target end, Remaining (days), Findings and Updated. Missing values show as "Unknown", styled differently; the table is sortable and read-only.
- Findings indicator: a count column, a tinted row, and a tooltip that lists the findings.
- Manual refresh (button and F5): the service runs on a worker thread, the button is disabled meanwhile, a failed refresh keeps the previous data and shows a banner with the readable message, and warnings are shown.
- A status bar with ticket count, last refresh time, unreadable tickets and finding counts.
- "Open in Jira" (toolbar, context menu, double-click) opens the ticket only when the service says the link is safe.
- When Jira is not configured the window explains what to set instead of failing to start. The setup dialog itself is a later change.
- Dependencies: `PySide6-Essentials` (core, GUI and widgets only, not the full PySide6 with web engine) and `pytest-qt` for tests.

## Capabilities

### New Capabilities
- `dashboard-window`: The main window, ticket table, refresh, findings indicator, status bar and "Open in Jira".

### Modified Capabilities
- `project-foundation`: the source layout now includes a `ui` package (the "no premature folders" rule no longer lists `ui`).

## Impact

- Code: new `src/jira_dashboard/ui/` (application bootstrap, main window, table model, refresh worker); `jira_dashboard.main` launches it; tests in `tests/unit/` with `pytest-qt` running headless (`QT_QPA_PLATFORM=offscreen`).
- Dependencies: `PySide6-Essentials`, dev `pytest-qt`.
- Docs: README and `docs/dashboard.md`.
- Out of scope: details panel, filter bar, grouped (tree) view, first-run setup dialog, packaging to an installer, any write to Jira.
