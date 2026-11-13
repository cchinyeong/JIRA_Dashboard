# Proposal

## Why

Work at Dyson is tracked against project numbers. Jira's multi-select field "Dyson Project List" (`customfield_12901`) records which projects a ticket belongs to, for example `898B`, `1000` or `Transformation & Improvement`. Project Leads and Domain Leads think in projects: "show me everything for 898B". The dashboard does not read this field yet, so there is no way to filter by it. Live data shows it is set on 345 of the 353 tickets, and a ticket can carry several projects.

## What Changes

- Read the field from Jira (its ID goes into configuration, like the other custom fields) and map it into a new `Ticket.dyson_projects` tuple of option names, empty when the field is empty.
- Filter by it: the service's `TicketFilter` and facets gain a Dyson project criterion. Because a ticket can have several projects, a ticket matches when any of its projects is selected, and the facet counts a ticket once for each of its projects. Tickets with no value are counted and selectable as "Unknown".
- A "Dyson Project" multi-select in the filter bar, with counts, ordered naturally (915 before 1000, names after numbers) with "Unknown" last.
- The details panel shows the ticket's Dyson projects.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `jira-ticket-mapping`: maps the Dyson Project List field (ADDED requirement).
- `ticket-domain-model`: tickets carry their Dyson projects (ADDED requirement).
- `ticket-service`: filtering and facets cover the Dyson project (MODIFIED "Filtering" and "Facets for filter controls").
- `ticket-filter-bar`: a Dyson Project filter (MODIFIED "Filter controls").
- `ticket-details-panel`: shows the Dyson projects (ADDED requirement).

## Impact

- Code: `config/settings.py` and `default.toml` (new field ID), `integrations/jira_http.py` (requested fields and the field check), `integrations/jira_mapping.py`, `models/ticket.py`, `services/ticket_query.py`, `ui/filter_bar.py`, `ui/details_panel.py`.
- Tests: mapper, query, filter bar, panel and window tests extended; no live-data fixture change (the committed fixtures predate the field, so the mapper is tested with synthetic payloads).
- Docs: `docs/jira-integration.md`, `docs/configuration.md`, `docs/dashboard.md`.
- Out of scope: a table column for the project, grouping by project, a project dashboard, mapping project codes to names, and changing the sanitiser allow-list.
