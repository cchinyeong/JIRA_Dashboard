# Tasks

## 0. Model and configuration additions

- [x] 0.1 Add `TicketKind` and the defaulted `kind` and `parent_key` fields to the model; verify unit tests for the three kinds, default OTHER and parent key present/absent, and that existing tests still pass
- [x] 0.2 Add the `issues` settings (request and task types, overlap rejected, parent link phrases) and `fields.epic_link` (`customfield_10001`) to settings and `default.toml`, and document them in `docs/configuration.md`; verify tests for defaults and overlapping types

## 1. Mapping helpers

- [x] 1.1 Add `TicketMappingError` and helpers `seconds_to_days`, `parse_timestamp`, `map_user` in `integrations/jira_mapping.py`; verify unit tests for 115200 s to 4.0 days, absent values and `+0800` timestamps
- [x] 1.2 Add `parse_sprint` for legacy string and structured forms, choosing the active sprint; verify tests for names with spaces, parentheses and commas, closed-plus-active, `<null>` dates and empty field
- [x] 1.3 Add `extract_requester` using the configured panel title and placeholders; verify tests for filled panel with trailing period, placeholder `Requester`, empty panel and missing panel
- [x] 1.4 Add `map_kind` and `map_parent` (Epic Link first, then qualifying issue links, lowest key wins, tasks only); verify tests for Epic Link, "is child of" link to a Risk, "is caused by" link to an Issue, unrelated phrase, link to another Task, several qualifying links, request without parent and both link directions (inward and outward)

## 2. Issue mapper

- [x] 2.1 Add fixtures under `tests/unit/fixtures/`: the CAE-1558 Risk issue, a Task linked to an Epic by Epic Link and a Task linked to a Risk by issue link, without real credentials or internal hosts
- [x] 2.2 Implement `map_issue(payload, settings)` covering the core fields, status, kind, parent, dates, effort, domain, request drivers, sprint, requester and URL; verify tests against the fixtures, a reconfigured field ID, an unsupported status (error names the key) and that the payload is unchanged

## 3. Client

- [x] 3.1 Add the abstract `JiraClient` in `integrations/jira_client.py` with `get_ticket`, `get_tickets` and `search_tickets`; verify a test that it cannot be instantiated and a fake subclass returns `Ticket` models
- [x] 3.2 Add `JiraOnPremClient` with the placeholder guard (`JiraNotConfiguredError` naming `jira.base_url`) and `build_search_jql` with escaping; verify tests for project/team scope, active sprints, quote escaping and the guard
- [x] 3.3 Make the read methods raise not-implemented without network or secret access; verify a test that patches the socket layer and the secrets service and asserts neither is touched
- [x] 3.4 Export public names from `integrations/__init__.py`; verify `from jira_dashboard.integrations import JiraClient, JiraOnPremClient, map_issue` in a test

## 4. Docs and quality

- [x] 4.1 Write `docs/jira-integration.md` covering the interface, payload quirks handled, the query scope and what MVP-1 must still verify against live data; verify it matches the specs
- [x] 4.2 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass
