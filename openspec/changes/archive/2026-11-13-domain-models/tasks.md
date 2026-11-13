# Tasks

## 1. Enums

- [x] 1.1 Add `TicketStatus` (six values, `from_jira` lookup) and `UserRole` in `models/enums.py`, with unit tests for known, case-insensitive and unsupported (`IMPLEMENTED`) statuses; verify `uv run pytest` passes
- [x] 1.2 Add `Domain` with `from_simulation_type` (None/empty to `UNSPECIFIED`, unknown to `OTHER`) and tests; verify `uv run pytest` passes

## 2. Entities

- [x] 2.1 Add frozen `Project`, `Sprint` and `User` dataclasses; verify unit tests cover construction and immutability
- [x] 2.2 Add frozen `Ticket` with all specified fields, `request_drivers` tuple, effort in days and the derived `is_blocked` property; verify tests cover minimal ticket, multi-component drivers, blocked for REFINEMENT only, absent requester and rejected assignment
- [x] 2.3 Re-export all models from `models/__init__.py`; verify `from jira_dashboard.models import Ticket, TicketStatus` works in a test

## 3. Quality

- [x] 3.1 Verify `uv run ruff check`, `uv run ruff format --check` and `uv run pytest` all pass
- [x] 3.2 Document the status, domain and blocked semantics in `docs/domain-model.md`; verify it matches the specs
