# Proposal

## Why

The table shows twelve columns, but a ticket has more to say than fits in a row: the full description, who requested it, the dates, the parent, the sprint, and the full text of each data-quality finding with its suggested correction. Findings are the point of the last change, yet today a user can only read them as a tooltip. A details panel lets a user select a row and see everything the application knows about that ticket, still read-only.

## What Changes

- A details panel beside the table (a splitter, so it can be resized or collapsed) that shows the selected ticket.
- Sections: header (key, summary, status, type), people (assignee, reporter, requester), planning (domain, request drivers, sprint with state and dates, target start and end, actual start, completion, estimated and remaining effort in days, blocked state and reason), hierarchy (parent key, with the parent's summary and type when the parent is loaded), findings (each finding's message, field, related ticket and suggested correction), and description.
- Missing values read "Unknown" in the same style as the table. A non-standard status reads `Unknown (<raw name>)`.
- The description is shown formatted: Jira wiki markup (panels, headings, bold, italic, monospace, lists, tables, code blocks, links, mentions, images) is converted to a small safe subset of rich text so it reads as content, not formatting codes. All text is escaped first, so Jira content can never inject HTML, and no links or images are loaded; links are shown as text with their address, images as `[image: name]`.
- An "Open in Jira" button in the panel, using the same rule as the toolbar action.
- The selection is kept across a refresh when the ticket still exists; otherwise the panel returns to its empty state.

## Capabilities

### New Capabilities
- `ticket-details-panel`: The read-only details panel for the selected ticket.

### Modified Capabilities
<!-- None: the table, refresh and Open in Jira requirements of dashboard-window are unchanged. -->

## Impact

- Code: new `src/jira_dashboard/ui/details_panel.py`; `main_window.py` gains a splitter and wires selection to the panel. No service change: the parent is looked up with the existing `service.snapshot.get(key)`.
- Tests: `tests/unit/test_details_panel.py` and additions to `test_main_window.py` (headless, pytest-qt).
- Docs: `docs/dashboard.md`.
- Out of scope: editing or correcting anything (MVP-4), loading images or following links from the description, comments and history, filters, grouped view, setup dialog.
