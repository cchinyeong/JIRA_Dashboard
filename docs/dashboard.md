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

## Details panel

Select a row to see the whole ticket in the panel on the right (drag the divider to resize or collapse it). It is read-only and shows:

- **Overview, People, Planning:** status, type, priority, domain, request drivers; assignee, reporter, requester; sprint (name, state, dates), target and actual dates, created and updated, estimated and remaining days, and whether the ticket is blocked (Refinement) with its reason.
- **Hierarchy:** the parent key, plus the parent's type and summary when the parent was loaded.
- **Findings:** every finding with its message, the field, the related ticket and the suggested correction, or "No findings detected."
- **Description:** shown formatted. Jira markup (panel titles, headings, bold, italic, lists, tables, code blocks) is converted to readable text; images appear as `[image: name]` and links as "text (address)". Nothing is loaded or opened, and any HTML in the text is shown literally.

Missing values read *Unknown* in an italic, theme-aware style. The selection is kept after a refresh if the ticket is still there (the panel shows its new values); otherwise it is cleared. The panel's **Open in Jira** button follows the same rule as the toolbar action.

## Filtering

Above the data, once a refresh has succeeded, the filter bar narrows what is shown. Controls combine (a ticket must satisfy all of them); inside one drop-down any selected value matches.

- **Search** matches the key, summary, requester or assignee name, ignoring case.
- **Type, Status, Domain, Dyson Project, Assignee, Sprint, Priority** are drop-downs with check boxes. Each value shows its ticket count over *all* tickets, and "Unknown" is last. **Type** is the application's own grouping (Request = Epic, Risk or Issue; Task; Other), not the raw Jira issue type.
- **Dyson Project** comes from Jira's multi-select "Dyson Project List". A ticket can belong to several projects: it matches when *any* of its projects is selected, and it is counted once under each of them, so the counts can add up to more than the number of tickets. Projects are ordered naturally (898B, 915, 1000, then names). "Unknown" at the end means the ticket has no project; this is different from a project option that Jira literally names `unknown`, which is listed among the ordinary values. The details panel shows a ticket's projects.
- **Only with findings** keeps tickets that have data-quality findings.
- **Clear** resets everything.

Filters stay applied after a refresh; values that no longer exist (for example a finished sprint) are dropped. The status bar reads "40 of 353 tickets" while a filter is active, and if nothing matches the window says so.

## Table and Hierarchy views

Use the **Table** / **Hierarchy** switch at the right of the filter bar. Both use the same filter, the same details panel and the same Open in Jira action, and the selected ticket stays selected when you switch.

The hierarchy shows each request (Epic, Risk, Issue) with its Tasks beneath it. A parent that does not match the filter but has matching children is shown dimmed and in italics, so you can still see where the Task belongs. A **Tasks without a parent (n)** entry at the end lists Tasks that have no Epic Link and no "is child of" link, which is the data-quality finding to correct in Jira. The tree is expanded each time it is rebuilt.

## When something goes wrong

- A failed refresh keeps the previous tickets and shows a red banner with the reason. A refresh that succeeds with warnings (for example parent tickets that could not be loaded) shows them in an amber banner. Click `×` to dismiss; a later successful refresh clears it.
- If `jira.base_url` is not set, the window says so, Refresh is disabled and the **Jira setup** dialog opens (also reachable from the **Set up Jira…** button or the toolbar). Saving applies the address and token at once and starts a refresh; no restart is needed. If you cancel, the message and button stay.
- If no token is stored, the window shows the message and offers the same dialog (it opens once automatically). See [security.md](security.md) for what the dialog stores and where.
- If the environment variable `JIRA_DASHBOARD_JIRA__BASE_URL` is set, it overrides the settings file, so the dialog cannot change the address and says so.

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
