# Domain model

Internal models live in `jira_dashboard.models`. They are frozen dataclasses and know nothing about Jira payloads.

## Status

Six VE workflow statuses: `NEW`, `REFINEMENT`, `BACKLOG`, `PLANNED`, `IN_PROGRESS`, `CLOSED`. `IMPLEMENTED` is unused and rejected by `TicketStatus.from_jira`.

Board columns are display labels only and never drive logic. The Project Lead board shows `REFINEMENT` as "On Hold"; the Active Sprint board labels `BACKLOG` "On Hold" and `PLANNED` "In Review".

## Blocked

`Ticket.is_blocked` is derived and true only when the status is `REFINEMENT`. It is not stored.

## Domain and request drivers

- `domain` is the Jira Simulation Type (`Domain.from_simulation_type`): "None"/empty give `UNSPECIFIED`, unknown values give `OTHER`.
- `request_drivers` are the Jira Components (for example Risk, Issue, Verification).
- `dyson_projects` are the options selected in Jira's "Dyson Project List" (a tuple, possibly several, empty when unknown).
- The Jira Team field is used to scope which tickets are fetched, not stored as the domain.

## Units and requester

Effort is in days (floats). `requester` is free text, not a `User`.
