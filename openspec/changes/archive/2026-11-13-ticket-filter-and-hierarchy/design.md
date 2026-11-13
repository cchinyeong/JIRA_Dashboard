# Design

## Context

`TicketService` already offers `list_tickets(TicketFilter)`, `facets()` (values with counts, unknown last, non-standard status labelled with the raw name) and `grouped(tickets)` returning a `GroupedView` of `TreeNode(ticket, matched, children)` plus `orphans`. `MainWindow` holds a table model, a sort proxy, the details panel and a status bar. Selection is read through `_selected_ticket()` and re-applied after refresh by key. Everything needed from the service exists, so this change only adds UI.

## Goals / Non-Goals

**Goals:**
- Filter in one place for both views; keep the details panel and "Open in Jira" working in both.
- Reuse the service's filtering and grouping; no filtering logic in the UI.

**Non-Goals:**
- Saved filters, per-role defaults, date filters, editing, the setup dialog.

## Decisions

- **Filtering through the service, not the proxy.** The window keeps one `TicketFilter` and calls `service.list_tickets(filter)` to feed the table model and `service.grouped(tickets)` for the tree. Alternative: `QSortFilterProxyModel` filtering; rejected because the rules (including the text search fields) already exist and are tested in the service, and the tree needs the matched list anyway.
- **`FilterBar(QWidget)`** in `ui/filter_bar.py`: a `QLineEdit` (debounced about 250 ms with a single-shot timer), six `FacetButton`s (a `QToolButton` with a menu of checkable actions, text "Status (2)" when values are selected), a check box and a Clear button. It exposes `set_facets(facets)` and emits `changed(TicketFilter)`. Facet menus show "label (count)". `set_facets` rebuilds the menus, keeps still-valid selections and drops the rest, then emits `changed` only if the filter value changed. Alternative: combo boxes (single choice); rejected, multi-select is the point.
- **Facet fields to filter attributes:** Type uses the `kind` facet (Request, Task, Other), plus a note in the docs; Status, Domain, Assignee, Sprint, Priority map to their facets. Facet values are used as the filter's `frozenset` members, so unknown (`None`) is selectable like any other.
- **Views:** a `QStackedWidget` holds the existing table and a `QTreeView`; a two-button segmented control ("Table", "Hierarchy", checkable `QToolButton`s in an exclusive group) in the filter bar's row switches it. The details panel stays outside the stack so it serves both.
- **`HierarchyModel(QStandardItemModel)`** in `ui/hierarchy_model.py`: `set_view(GroupedView)` builds items recursively. Columns: Key / Summary (key then summary in one cell, as the first column carries the tree arrows), Type, Status, Assignee, Sprint, Target end, Findings. It reuses the table's formatting, unknown-style and finding-tint code by sharing helper functions from `ui/formatting.py` and the model's brushes. Unmatched (context) nodes use the palette's disabled colour and italic; matched nodes the normal colours. Each item stores its `Ticket` in `TICKET_ROLE`. The orphans become a top-level item "Tasks without a parent (n)" (not selectable as a ticket) with their rows beneath; the item is omitted when there are none.
- **Selection:** the tree's selection model feeds the same `_update_actions` path as the table; `_selected_ticket()` returns the selected ticket of whichever view is current (a group node has none). After a refresh the selection is restored by key in the current view only.
- **Refresh:** on success the window refreshes facets (`service.facets()`) into the filter bar, then applies the filter. `changed` while a refresh is running is fine since both only read the snapshot.
- **Empty result:** when the filtered list is empty but the snapshot is not, the stack shows a message page ("No ticket matches the filters." with the Clear button reachable in the bar) instead of an empty table.
- **Status bar:** "x of y tickets" when the filter is non-default, using `len(shown)` and the summary total.
- **Expansion:** `expandAll()` after each rebuild; simple and predictable for a few hundred rows. Collapse state is not preserved.
- **Testing:** pytest-qt, offscreen. Filter bar tests use a handcrafted facet dict. Hierarchy model tests build a `GroupedView` from tickets through the real `group()` and `make_snapshot()`. Window tests extend the existing fake service with `facets`, `list_tickets(criteria)` and `grouped`, reusing the real functions from `ticket_query` so the fake cannot drift.

## Risks / Trade-offs

- [Rebuilding the whole tree on each filter change] → a few hundred rows; measured acceptable, with the text debounce preventing per-keystroke rebuilds.
- [Dimmed context parents might be mistaken for matches] → italic plus disabled colour, and the status bar counts only matches.
- [Two views double the selection code] → one `_selected_ticket()` and one update path, covered by tests in both views.
- [Facet lists can be long (assignee, sprint)] → menu scrolls; a search inside the menu is left for later.
- [Fake service drift in tests] → the fake delegates to the real query functions.
