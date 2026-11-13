# Proposal

## Why

The dashboard UI must never call Jira or hold business logic. Between the finished Jira client and the coming PySide6 window there is nothing yet: no place that refreshes data, keeps it consistent while a refresh runs in the background, loads the parents the client does not return, filters, groups and summarises tickets, or turns Jira failures into something the UI can show. MVP-1 acceptance needs exactly that: retrieve VE tickets, search and filter them, refresh on demand, open the original ticket, and cope with an unavailable Jira.

## What Changes

- Add a `TicketService` in `services` that refreshes from a `JiraClient`: team search, then the parents of retrieved tickets that were not in the result (up to three levels, for Task, Risk or Issue, Epic).
- Keep an immutable in-memory snapshot (tickets, parent context, unreadable-ticket failures, warnings, refresh time) that is replaced only by a successful refresh, so a failed or running refresh never leaves the UI with partial or empty data.
- Turn failures (authentication, network, timeout, missing token) into a result the UI can show, without raising; allow only one refresh at a time.
- Add filtering by project, domain, assignee, sprint, status, priority, kind, free text and "has findings", with unknown values selectable, plus facets (distinct values with counts) for the filter controls.
- Add natural ticket ordering, parent and children lookup, a grouped view (tickets under their parents, orphan Tasks listed apart), and a summary (counts by kind, status and finding code).
- Give a ticket's Jira link only when it belongs to the configured Jira.

## Capabilities

### New Capabilities
- `ticket-service`: Refresh, snapshot, filtering, hierarchy and summary of Jira tickets for the UI, independent of the UI toolkit and read-only.

### Modified Capabilities

## Impact

- Code: `src/jira_dashboard/services/` (`ticket_service.py`, `ticket_query.py`) and tests in `tests/unit/` using a fake `JiraClient`.
- No new dependencies and no new settings.
- Docs: `docs/ticket-service.md`.
- Out of scope: the PySide6 window and widgets, persistence or offline cache, background threading (the UI starts the refresh on a worker thread), first-run setup, any write to Jira.
