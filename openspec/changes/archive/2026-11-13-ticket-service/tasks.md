# Tasks

## 1. Query functions

- [x] 1.1 Add `ticket_query.py` with natural key ordering, `TicketFilter` and `filter_tickets` (AND across criteria, OR within, empty applies nothing, unknown via `None`, free text, has-findings); verify tests for combined criteria, unknown assignee, text search by key and summary, findings only, and an empty filter returning everything
- [x] 1.2 Add `facets` with values, labels and counts, unknown last, UNKNOWN statuses labelled with the raw name; verify tests for the assignee example (3, 1, unknown 2), sprint, status and kind facets
- [x] 1.3 Verify natural ordering with CAE-100, CAE-99 and CAE-1000, other project prefixes, and an unparsable key sorting last

## 2. Snapshot, hierarchy, summary

- [x] 2.1 Add `Snapshot` and `make_snapshot` (tickets, context, failures, warnings, refreshed_at, key index with `get`); verify tests for lookup in both groups and immutability
- [x] 2.2 Add `children_of`, `parent_of` and `group` returning `GroupedView(roots, orphans)` with `TreeNode(ticket, children, matched)`, cutting parent cycles; verify tests for Task under Risk under Epic, a filtered-out parent shown unmatched, orphan Tasks, a parent missing from the snapshot, and a cycle
- [x] 2.3 Add `summarise` returning counts by kind, status and finding code, tickets with findings, unreadable tickets and the refresh time; verify the 3 Tasks and 2 Risks example

## 3. Refresh

- [x] 3.1 Add `TicketService` and `RefreshResult` with refresh = search then up to three rounds of parent retrieval, atomic snapshot replacement, and an injectable clock; verify tests with a fake `JiraClient` for parents outside the search, parent of a parent, a missing parent, remembered missing keys not re-requested, and the depth limit
- [x] 3.2 Map failures to results without raising (`auth`, `timeout`, `connection`, `tls`, `http`, `no_token`, `unexpected` logged with a traceback), keep previous data on failure, and make a parent-round failure a warning; verify tests for each kind, previous data kept, first refresh failing, and the warning case
- [x] 3.3 Add the single-refresh guard returning `busy`; verify a test where a second refresh is requested from another thread while the first waits on an event, the client being called once, and readers getting the previous snapshot meanwhile
- [x] 3.4 Add `ticket_link` allowing only URLs under the configured Jira base URL; verify a foreign and a malformed URL give nothing
- [x] 3.5 Verify the services package imports without any GUI module (block `PySide6` in the test) and that the service calls only read methods of a recording client

## 4. Docs and quality

- [x] 4.1 Write `docs/ticket-service.md` (what the UI calls, the result and snapshot types, refresh behaviour, filter semantics, threading guidance for the UI); verify it matches the specs
- [x] 4.2 Run the service once against the real Jira, read-only, and confirm the ticket count, the number of parents loaded and the summary look right, then verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass

## Workflow follow-up

- Next MVP-1 changes: the PySide6 window (table, details, filters, refresh, open in Jira, findings) and first-run setup (URL and PAT dialog).
