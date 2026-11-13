# Tasks

## 1. Filter bar

- [x] 1.1 Implement `FacetButton` (checkable menu entries "label (count)", selected count in the button text, unknown last) and `FilterBar` (debounced search, six facet buttons, findings switch, Clear, `set_facets`, `changed(TicketFilter)`); verify headless tests for combining several filters, several values of one filter, text search after the debounce, findings switch, Clear returning to the neutral filter, counts and unknown-last in the menus, and the non-standard status label
- [x] 1.2 Make `set_facets` keep still-valid selections and drop vanished values without emitting when the filter is unchanged; verify tests for a kept filter and a disappeared sprint

## 2. Hierarchy view

- [x] 2.1 Implement `HierarchyModel` building items from a `GroupedView` with the seven columns, dimmed unmatched nodes, the "Tasks without a parent (n)" node (omitted when empty), tickets stored in `TICKET_ROLE`, and finding tint, tooltip and unknown style shared with the table; verify tests for a Task under its Epic, several tasks in key order, a dimmed non-matching parent, orphans with count, no orphan node, and finding display
- [x] 2.2 Share the unknown-style and finding-tint helpers between the table model and the hierarchy model; verify the existing table model tests still pass unchanged

## 3. Window integration

- [x] 3.1 Add the filter bar, the Table/Hierarchy switch and the stacked table and tree to `MainWindow`, feed both views from `service.list_tickets(filter)` and `service.grouped(...)`, feed facets after each refresh, and show "x of y tickets" while filtered; verify window tests with the fake service for filtering the table, switching view, the status bar text and the filter surviving a refresh
- [x] 3.2 Make selection, the details panel and Open in Jira work in both views, restore the selection by key after refresh in the current view, and ignore group nodes; verify tests for tree selection filling the panel, Open in Jira from the tree, a selected group node showing the hint, and selection kept across refresh in the tree
- [x] 3.3 Show the "No ticket matches the filters" message when the filtered list is empty; verify a test that the message appears and disappears after Clear

## 4. Docs and checks

- [x] 4.1 Update `docs/dashboard.md` (filter bar, counts, Type filter meaning, the two views, dimmed parents, the "Tasks without a parent" node) and verify it matches the behaviour
- [x] 4.2 Run the real application against the real Jira, check filters, both views, the orphan node count (61 expected) and the dark theme, then verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass
