# Ticket service

`jira_dashboard.services.ticket_service.TicketService` is what the user interface talks to. The UI never calls Jira, the client or the query helpers directly. The service has no GUI dependency, never writes to Jira, and holds all refresh, filter and grouping logic.

```python
service = TicketService(JiraOnPremClient(settings), settings)
result = service.refresh()  # call from a worker thread
tickets = service.list_tickets(TicketFilter(statuses=frozenset({TicketStatus.IN_PROGRESS})))
```

## Refresh

`refresh(in_sprints_only=False)` returns a `RefreshResult` and never raises:

| `status` | Meaning |
|---|---|
| `ok` | Data replaced. `warnings` may say parents could not be loaded or the hierarchy is deeper than three levels. |
| `failed` | Previous data kept. `error_kind` is `auth`, `timeout`, `connection`, `tls`, `http`, `no_token` or `unexpected`; `message` is user-readable. |
| `busy` | Another refresh is running; nothing was started. |

Steps: team search, then up to three rounds of loading the parents (Task, Risk or Issue, Epic) that the search did not return. Parents loaded only to complete the hierarchy are in `snapshot.context`: reachable by `snapshot.get(key)`, but not in the ticket list. A parent that does not exist or cannot be seen is simply absent; it is not asked for twice in one refresh. Tickets that could not be read are listed in `snapshot.failures`.

## Snapshot

`service.snapshot` is an immutable `Snapshot` (`tickets`, `context`, `failures`, `warnings`, `refreshed_at`). It is replaced as a whole when a refresh succeeds, so a thread reading it during a refresh sees the previous complete data, never a mixture. A failed or running refresh changes nothing.

## Filtering

`TicketFilter` fields: `projects`, `domains`, `assignees` (usernames), `sprints` (names), `statuses`, `priorities`, `kinds`, `text`, `only_with_findings`. Values of one field are alternatives; different fields all apply; an empty field restricts nothing. Put `None` in a set to select unknown (no assignee, no sprint, no priority, unspecified domain). `text` is a case-insensitive substring over key, summary, assignee name and requester.

`service.facets()` returns, per field, the values present with counts and display labels (unknown last; a non-standard status is labelled with its raw name, for example "Unknown (Implemented)"). Tickets are ordered by project and then numerically (CAE-99 before CAE-100).

## Hierarchy and summary

`service.grouped(tickets=None)` returns a `GroupedView`: `roots` (a tree of `TreeNode(ticket, matched, children)`) and `orphans` (Tasks with no parent key). A ticket is shown under its parent even when the parent is outside the list or excluded by a filter (`matched=False`). `children_of` and `parent_of` in `ticket_query` look up single steps.

`service.summary()` counts tickets by kind, issue type and status, tickets with findings, findings by code, unreadable tickets, and gives the last refresh time.

## Opening a ticket

`service.ticket_link(ticket)` returns the ticket's Jira URL only when it is `https` on the configured Jira host, otherwise `None`. The UI must open nothing else.

## Threading guidance for the UI

Run `refresh()` on a worker thread and show "refreshing" meanwhile; read `service.snapshot` and the query methods from the UI thread. A second refresh while one runs returns `busy` at once, so the refresh button can simply be ignored or disabled during a refresh.
