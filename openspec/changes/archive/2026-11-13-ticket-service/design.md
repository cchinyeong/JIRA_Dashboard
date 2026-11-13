# Design

## Context

Done and archived or ready: `JiraClient` (`get_ticket`, `get_tickets(keys)`, `search_tickets`) returning `TicketBatch` with failure records, `JiraApiError` kinds (`auth`, `not_found`, `timeout`, `connection`, `tls`, `http`), `MissingSecretError`, and tickets with `parent_key`, `kind`, `findings`. A live search takes about 7 s and returns about 350 tickets, so the UI will call refresh on a worker thread. Search results do not contain the parents of sprint Tasks (confirmed live), which is why the service loads them. `data-quality-findings` is implemented and unarchived; this change only reads `Ticket.findings`.

## Goals / Non-Goals

**Goals:**
- Everything the dashboard shows or does with ticket data lives in plain, testable Python.
- Readers and the background refresh never conflict, and failures never blank the UI.

**Non-Goals:**
- Threads or Qt signals, persistence, caching across runs, the PySide6 window, any Jira write.

## Decisions

- **Two modules:** `services/ticket_query.py` holds pure functions and value types (filter, facets, natural order, hierarchy, summary); `services/ticket_service.py` holds the stateful `TicketService`. Pure functions take a snapshot or a ticket list, so tests need no client.
- **Snapshot:** a frozen dataclass `Snapshot(tickets, context, failures, warnings, refreshed_at)` plus a key index built once in a `make_snapshot` factory. `tickets` are the search results; `context` are parents loaded only to complete the hierarchy. `get(key)` looks in both. Replaced atomically by assigning one reference, which is safe for readers in other threads in CPython and needs no lock on the read path.
- **Refresh algorithm:** `search_tickets()`; then up to three rounds of `get_tickets(missing parent keys)` where missing = parents of everything gathered so far that are not yet gathered; keys that come back absent are remembered so they are not asked again. Search failure aborts the refresh; a failure in a parent round ends the loop with a warning and keeps what was gathered.
- **Result type:** `RefreshResult(status, error_kind, message, warnings, counts)`; `status` is `ok`, `failed` or `busy`. `JiraApiError.kind`, `MissingSecretError` (kind `no_token`) and any other exception (kind `unexpected`, logged with the traceback) are mapped here. Nothing raises. Alternative: let exceptions propagate and make the UI map them; rejected, because every caller would repeat the mapping.
- **One refresh at a time:** a `threading.Lock` acquired non-blocking in `refresh()`; losing the race returns `busy` at once.
- **Clock:** `TicketService(client, settings, clock=datetime.now)` so tests control `refreshed_at`; timestamps are timezone-aware.
- **Filter:** frozen `TicketFilter` with `frozenset` fields; `None` inside a set means "unknown". Matching: every non-empty criterion must match (AND), any value inside one criterion (OR). Text search is a case-insensitive substring over key, summary, assignee display name and requester. Alternative: a free-form query language; rejected as more than MVP-1 needs.
- **Facets:** `facets(tickets) -> dict[field, list[FacetValue(value, label, count)]]`, sorted by label with "Unknown" last. Assignee value is the username (label the display name); sprint value and label the name; status label shows the raw name for UNKNOWN statuses ("Unknown (Implemented)").
- **Natural order:** sort key `(project prefix, number)` parsed from the key; a key that does not parse sorts last by text. JQL's `ORDER BY key` is textual, so the service re-sorts.
- **Hierarchy:** `children_of`, `parent_of`, and `group(tickets, snapshot) -> GroupedView(roots, orphans)`. A node is `TreeNode(ticket, children, matched)`. Each ticket is attached to its parent looked up in the snapshot, and parents are chained upward to the root; parent nodes not in the list are `matched=False`. Tasks without `parent_key` go to `orphans`. A parent cycle is cut by a visited set.
- **Summary:** `summarise(snapshot)` returns a frozen `Summary` with `Counter`-based dictionaries keyed by enum values.
- **Safe link:** `ticket_link(ticket)` returns `jira_url` only if it starts with `settings.jira.base_url + "/"`; the UI opens nothing else.
- **Imports:** the services package imports no GUI module; a test imports it with `PySide6` blocked.

## Risks / Trade-offs

- [A refresh that is slow keeps the old data on screen] → That is the intent; the UI shows "refreshing" and the last refresh time.
- [Parent rounds add requests] → At most three small batched requests; parents are usually few (about 80 of 141 Tasks have one, many shared).
- [Atomic reference swap relies on CPython semantics] → Documented; the snapshot is immutable so no reader sees half-built data in any case.
- [Facet or filter on a field whose value is a name may collide] → Usernames and project keys are used as values; labels only for display.
- [Unexpected exceptions are swallowed into a result] → Logged with a traceback, kind `unexpected`, so they are visible in the log and in the UI message.
