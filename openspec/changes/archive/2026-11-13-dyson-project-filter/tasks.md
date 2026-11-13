# Tasks

## 1. Model, configuration and mapping

- [x] 1.1 Add `Ticket.dyson_projects` (default empty), the `dyson_project_list` field ID in settings and `default.toml`, and include it in the requested fields and the field check; verify tests that the setting loads from the default, can be overridden, appears in the requested fields, and that a ticket defaults to no projects
- [x] 1.2 Map the field in `jira_mapping.py` (option objects, plain strings, null; strip, drop blanks, de-duplicate, keep order; reconfigured ID); verify mapper tests for several projects, empty, null, blank and repeated names, an option named `unknown` kept as a value, and a reconfigured ID

## 2. Filtering and facets

- [x] 2.1 Add the `dyson_projects` criterion to `TicketFilter` with any-match semantics and unknown for an empty list; verify query tests for a ticket in two projects matched by either, an unknown-only selection, and combination with another criterion
- [x] 2.2 Count each ticket once per project in `facets()` with natural ordering (numbers before names, unknown last) for this facet only; verify tests for the counts, the order `898B`, `915`, `1000`, `Transformation & Improvement`, and an unknown entry only when needed

## 3. Window

- [x] 3.1 Add the "Dyson Project" filter button after Domain and show "Dyson projects" in the details panel; verify filter bar tests for selecting a project (with counts in the menu) and a combined filter, panel tests for several projects and none, and a window test for filtering the table by project
- [x] 3.2 Update `docs/jira-integration.md`, `docs/configuration.md` and `docs/dashboard.md` (the field, any-match semantics, counts that can exceed the total, the `unknown` option versus "Unknown"); verify the text matches the behaviour

## 4. Live check

- [x] 4.1 Run against the real Jira and confirm the filter lists the project codes with counts, a multi-project ticket appears under each of its projects, and `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass
