# Proposal

## Why

353 tickets in one flat table is hard to work with. A Project Lead wants to see "everything In Progress for the Dynamic domain assigned to Max", a Domain Lead wants one domain's backlog, and everyone needs to see which Tasks belong to which Epic, Risk or Issue, and which Tasks have no parent at all (the data-quality finding the team asked to highlight). The service already provides filtering, facet counts and a parent/child grouping (`TicketFilter`, `facets()`, `grouped()`); the window does not use them yet. This change adds the filter bar and a hierarchy view on top of them. It is the last piece of MVP-1 except the first-run setup dialog.

## What Changes

- A filter bar above the table with: a text search (key, summary, requester, assignee), drop-down multi-select filters for Type (kind), Status, Domain, Assignee, Sprint and Priority, an "Only with findings" check box, and a Clear button. Each drop-down lists its values with counts from the whole refresh data, with "Unknown" last.
- A view switch, "Table" and "Hierarchy". Hierarchy shows a tree: Requests (Epic, Risk, Issue) with their Tasks beneath, built from the parent links. Parents that were loaded only for context and do not match the filter are shown dimmed so the structure stays visible. Tasks without a parent are listed under a separate "Tasks without a parent" node, so the data-quality problem is visible at a glance.
- Both views share the filter, the details panel and the selection: selecting a ticket in either shows it in the details panel, and "Open in Jira" works in both.
- The status bar shows "x of y tickets" when a filter is active.
- Filters and the chosen view survive a refresh; filter values that no longer exist are dropped.

## Capabilities

### New Capabilities
- `ticket-filter-bar`: Text search, multi-select filters, findings-only switch, clear, counts, persistence across refresh.
- `ticket-hierarchy-view`: Tree of requests and their tasks, dimmed context parents, the "Tasks without a parent" node, shared selection.

### Modified Capabilities
- `dashboard-window`: the status bar summary shows "x of y" while a filter is active.

## Impact

- Code: new `ui/filter_bar.py` and `ui/hierarchy_model.py`; `main_window.py` gains the bar, a stacked table/tree and shared selection handling. No service change.
- Tests: headless tests for the filter bar, the hierarchy model and the window wiring; existing window tests stay green.
- Docs: `docs/dashboard.md`.
- Out of scope: saved filters or views, role-based default filters (MVP-2), date-range filters, correcting findings (MVP-4), the setup dialog.
