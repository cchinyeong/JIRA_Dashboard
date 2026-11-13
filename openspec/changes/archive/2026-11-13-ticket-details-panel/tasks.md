# Tasks

## 1. Shared formatting

- [x] 1.1 Move the date, days, status and unknown-text helpers from `ui/ticket_model.py` into `ui/formatting.py` and import them in the model; verify `uv run pytest tests/unit/test_ticket_model.py` still passes unchanged

## 2. Panel

- [x] 2.1 Implement `DetailsPanel` with header, People, Planning (including sprint name, state and dates, and the blocked state and reason), Hierarchy, Findings and Description sections, plain-text only, palette-based unknown style, and the empty-state hint; verify headless tests for a full ticket, an empty selection, unknown values, the non-standard status, a sprint with dates, a blocked ticket, and parent loaded, not loaded and none
- [x] 2.2 Show every finding with message, field, related ticket and suggestion, or "no findings detected"; verify tests for a ticket with findings and one without
- [x] 2.3 Show the description with Jira markup converted to safe rich text (`ui/jira_markup.py`, escape first) in a read-only browser with links disabled, and "Unknown" when empty; verify converter tests for panels, headings, emphasis, lists, tables, code blocks, images, links, mentions and escaping of HTML, and a panel test that markup codes do not appear while `<b>` and `<script>` text stays literal
- [x] 2.4 Add the Open in Jira button that emits `open_requested` and is disabled without a link; verify tests for enabled with a link, disabled without one, and the signal

## 3. Window integration

- [x] 3.1 Put the table and panel in a splitter in `MainWindow`, update the panel on selection (parent via `service.snapshot.get`, link via `service.ticket_link`) and connect the button to `open_selected`; verify window tests with the fake service for selecting a row, clearing the selection, parent lookup, and the button opening the allowed link
- [x] 3.2 Keep the selection across refresh by key, clearing it when the ticket is gone; verify tests for a ticket still present with changed values and a ticket that disappeared

## 4. Docs and checks

- [x] 4.1 Update `docs/dashboard.md` with the panel (sections, plain-text description, selection across refresh); verify the text matches the behaviour
- [x] 4.2 Run the real application against the real Jira, confirm the panel for a Task with a finding, a ticket with a parent, and a closed ticket in the dark theme, then verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass
