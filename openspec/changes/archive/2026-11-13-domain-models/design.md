# Design

## Context

`jira_dashboard.models` exists but is empty (see the archived `project-scaffold`). Field IDs, units and status/board semantics were established during exploration: custom fields live in the integration layer, effort arrives from Jira in seconds, and the PL board and Active Sprint board use different column labels for the same statuses.

## Goals / Non-Goals

**Goals:**
- Pure, dependency-free models usable by every later layer.
- Encode the VE-specific semantics (six statuses, domain = Simulation Type, derived blocked).

**Non-Goals:**
- Parsing Jira payloads, converting seconds to days, or extracting the requester (`jira-client-interface`).
- Configurable blocked statuses or board column maps (`app-config`).
- Health, confidence or follow-up models (later MVPs).

## Decisions

- **Frozen dataclasses with `slots=True`**, one module per concept (`ticket.py`, `user.py`, `sprint.py`, `project.py`, `enums.py`), re-exported from `models/__init__.py`. Alternative: pydantic models; rejected because the models need no validation at this layer, and validation belongs at the Jira boundary.
- **Enums are `StrEnum`** so values serialise as plain strings. Status names mirror Jira names with spaces replaced by underscores.
- **`Domain.from_simulation_type(text)`** normalises case and whitespace; "None"/empty give `UNSPECIFIED`, unknown values give `OTHER`. This keeps new Jira options from breaking parsing.
- **`TicketStatus` lookup via `TicketStatus.from_jira(name)`** that normalises case and spaces and raises `ValueError` for unknown names; failing loudly surfaces workflow changes. The unused `IMPLEMENTED` is deliberately absent.
- **`Ticket.is_blocked` is a property** returning `status is TicketStatus.REFINEMENT`. It is not a field, so it cannot drift from the status. When `app-config` adds configurable blocked statuses, the property's rule is the single place to change.
- **`request_drivers: tuple[str, ...]`** (immutable, ordered, free strings) because Component names are an open set.
- **`estimated_effort` / `remaining_effort: float | None`** in days; the 8 h/day conversion happens in the integration layer.
- **Dates:** target and actual dates and completion are `date`; `created_date`/`updated_date` are timezone-aware `datetime`.
- **`assignee` and `reporter` are `User | None`; `requester` is `str | None`.** `User` has a username key, display name, optional email and optional role.

## Risks / Trade-offs

- [Blocked rule hard-coded to REFINEMENT] → Documented, tested, and isolated in one property for `app-config` to parameterise.
- [Raising on unknown status could fail a whole sync if Jira adds a status] → The integration layer is expected to catch and log per ticket; acceptable for now.
- [Fixed field set may miss later needs] → Frozen dataclasses make adding optional fields with defaults backwards compatible.
