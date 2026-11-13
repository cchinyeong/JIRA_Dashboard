# Proposal

## Why

Every later MVP (dashboards, health, write-back, forecasting) operates on internal models rather than Jira payloads. MVP-0 requires these models to exist first. Exploration with the VE team also showed that the spec's draft model does not match their Jira: the workflow has six statuses (not `TO_DO/IN_PROGRESS/BLOCKED/DONE`), "domain" is the Simulation Type, and "blocked" is not an independent concept.

## What Changes

- Add immutable (frozen dataclass) models in `jira_dashboard.models`: `Ticket`, `User`, `UserRole`, `Domain`, `Sprint`, `Project`, plus a `TicketStatus` enum.
- `TicketStatus` has the six VE workflow statuses: `NEW`, `REFINEMENT`, `BACKLOG`, `PLANNED`, `IN_PROGRESS`, `CLOSED`. `IMPLEMENTED` is unused and excluded.
- `UserRole` has `PROJECT_LEAD`, `DOMAIN_LEAD`, `DOMAIN_ENGINEER`.
- `Domain` mirrors the Jira Simulation Type values (Static, Dynamic, Optics, Thermal, Moldflow, CFD, Acoustic, Multiphysics, Other) plus `UNSPECIFIED`.
- `Ticket` carries the spec's minimum fields, plus `issue_type` and `request_drivers` (from Jira Components, e.g. Risk, Issue, Verification). Efforts are float days.
- `is_blocked` is derived: true only when the status is `REFINEMENT` (the Project Lead board's "On Hold"). Active Sprint board column names never affect it.
- `requester` is optional free text, not a `User`.

## Capabilities

### New Capabilities
- `ticket-domain-model`: Internal, Jira-independent representation of tickets, sprints, projects, users, roles and domains, including status semantics and derived blocked state.

### Modified Capabilities

## Impact

- Code: `src/jira_dashboard/models/**`; tests in `tests/unit/`.
- No new dependencies (standard-library dataclasses and enums).
- Out of scope: Jira payload mapping and requester parsing (`jira-client-interface`), configurable blocked statuses and board column maps (`app-config`), health models (MVP-3).
