# Design

## Context

`request_drivers` (Jira components) is the precedent for a multi-valued field: configured field ID in `settings.py`/`default.toml`, listed in the requested fields in `jira_http.py`, mapped to a `tuple[str, ...]` in `jira_mapping.py`. Filtering and facets live in `ticket_query.py`: `EXTRACTORS` maps a facet name to a function returning one value per ticket, and `matches()` tests membership. The filter bar builds its buttons from `FACET_FIELDS`. Live data (read-only probe, 353 tickets): `customfield_12901` is a multi-select option field, set on 345 tickets, and values include `898B`, `1000`, `915`, `Transformation & Improvement` and an option literally named `unknown`.

## Goals / Non-Goals

**Goals:**
- Filter by Dyson project in the service and the window, correct for tickets with several projects.
- Keep the field ID in configuration only.

**Non-Goals:**
- A table column, grouping by project, project names or dashboards.

## Decisions

- **Model:** `Ticket.dyson_projects: tuple[str, ...] = ()`, next to `request_drivers`.
- **Config:** new field role `dyson_project_list = "customfield_12901"` alongside the other IDs, so reconfiguration needs no code change. It is added to the requested fields and to the field-ID check (`check_fields`), so the live check reports it if it ever disappears.
- **Mapping:** accept a list of option objects (`{"value": ...}`), plain strings, or null; take each option's `value`, strip it, drop blanks, keep first occurrence order. Anything else (a scalar, a malformed element) maps to an empty tuple for that element, never an exception, following the mapper's existing tolerance. A raw option named `unknown` is a real value and stays; it is not turned into "no project".
- **Multi-valued filtering:** `EXTRACTORS` entries return a single value today. Introduce a parallel `MULTI_EXTRACTORS` (or let an extractor return a tuple) used by both `matches()` and `facets()`: a ticket matches when the selected set intersects its values, and an empty tuple counts as the unknown value `None`. Facets count a ticket once per value, so counts can exceed the ticket total; the docs say so. Alternative: one value per ticket (the first); rejected, it hides tickets that belong to several projects.
- **Natural ordering:** facet values for this field are sorted with a key that orders numeric prefixes by number and then by suffix (`898B` before `915` before `1000`), names after numbers, case-insensitive, with unknown last. The other facets keep their existing alphabetical order.
- **Distinguishing "unknown" values:** the facet's "Unknown" entry means no project; the option named `unknown` appears among the ordinary values with its own count. Both can exist; the docs explain the difference. Renaming either was considered and rejected as it hides Jira's own data.
- **UI:** one more `FACET_FIELDS` row, `("Dyson Project", "dyson_project", "dyson_projects")`, placed after Domain; `FilterBar.current_filter` already builds the filter from that table. The details panel gets a "Dyson projects" row in Planning.
- **Testing:** mapper tests with synthetic payloads (several, empty, null, reconfigured ID, blank and duplicate names, string and option forms); query tests for any-match, unknown, counts per project, natural order; filter bar and panel tests extending the existing ones. No fixture files change.

## Risks / Trade-offs

- [Counts that sum to more than the ticket total may confuse] → documented; the status bar still reports tickets, not memberships.
- [Option named `unknown` next to the "Unknown" entry] → both shown with distinct labels and counts; documented.
- [Field ID differs on Jira Cloud] → it is configuration, so migration changes a setting, not code.
- [A schema change to `Ticket` touches many constructors] → the new field has a default, so existing code and tests are unaffected.
