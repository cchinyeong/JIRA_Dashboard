# Dashboard window

`uv run jira-dashboard` opens the main window and starts a refresh automatically. The window appears first; tickets arrive when the refresh finishes (about 7 seconds against the real Jira).

## What you see

A read-only table of the team's tickets (see [ticket-service.md](ticket-service.md) for what is loaded).

| Column | Meaning |
| --- | --- |
| Key | Jira key, sorted numerically (CAE-99 before CAE-100) |
| Summary | Ticket title |
| Type | Jira issue type |
| Status | The six standard statuses; a non-standard one reads `Unknown (<name in Jira>)` |
| Priority, Assignee, Domain, Sprint | As recorded in Jira |
| Target end | Target end date |
| Remaining (days) | Remaining effort in days (8 hours per day) |
| Findings | Number of data-quality findings (see [data-quality.md](data-quality.md)) |
| Updated | Last update in Jira |

- A missing value reads **Unknown** in grey italics. Nothing is guessed.
- A ticket with findings has a tinted row. Hover over it to read each finding and its suggested correction.
- Click a column header to sort, click again to reverse. Unknown values always sort last.

## Actions

- **Refresh** (toolbar or `F5`) reloads in the background. The button is disabled and a progress bar shown while it runs.
- **Open in Jira** (toolbar, right-click, or double-click) opens the selected ticket in your browser. It is unavailable if the ticket has no link on the configured Jira host.

## When something goes wrong

- A failed refresh keeps the previous tickets and shows a red banner with the reason. A refresh that succeeds with warnings (for example parent tickets that could not be loaded) shows them in an amber banner. Click `×` to dismiss; a later successful refresh clears it.
- If `jira.base_url` is not set, the window says so and Refresh is disabled. Set it in `settings.local.toml` (see [configuration.md](configuration.md)) and restart.
- If no token is stored, the window shows the instructions in [security.md](security.md). Store the token, then press Refresh.

The status bar shows the ticket count, the time of the last successful refresh, the number of unreadable tickets and the number of tickets with findings.

## Development notes

- All Jira access goes through `TicketService`; the window only calls `refresh()` from a background thread (`ui/refresh_worker.py`).
- Tests run headless: `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`.
- The virtual environment lives inside the OneDrive folder by default, which can lock or sync files. Consider keeping it elsewhere:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\jira-dashboard-venv"
uv sync
uv run jira-dashboard
```
