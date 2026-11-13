# Design

## Context

The live run (see archived `jira-http-client`) returned 352 tickets and 3 failure records; the failures were all status "Implemented". Among the 352: 141 Tasks, 61 of them without a parent; 119 Risks and Issues, some linked to an Epic as "is child of" (4) or "created by" (5); and 2 Sub-tasks. `map_issue` is strict (any missing or unsupported value raises `TicketMappingError`), `TicketStatus.from_jira` raises on unknown names, and parent rules per kind are in `map_parent`.

## Goals / Non-Goals

**Goals:**
- Every retrieved ticket reaches the dashboard, with what needs correcting attached to it.
- Findings are pure functions of one payload: deterministic, testable, free of I/O.
- A model the MVP-4 correction flow can reuse (code, field, related ticket, suggested fix).

**Non-Goals:**
- Writing to Jira, any UI, cross-ticket or history-based checks, missing-estimate or stale-data health (MVP-3).

## Decisions

- **Model:** `FindingCode` (`StrEnum`: `NON_STANDARD_STATUS`, `TASK_WITHOUT_PARENT`, `REQUEST_WRONG_EPIC_LINK`, `INVALID_VALUE`) and a frozen `Finding(code, message, field=None, related_key=None, suggestion=None)` in `models`. `Ticket` gains `raw_status: str | None = None` and `findings: tuple[Finding, ...] = ()`. A tuple keeps the ticket immutable. `suggestion` is plain text for display now and the seed of the MVP-4 correction preview.
- **Unknown status:** `TicketStatus.UNKNOWN` is added; `TicketStatus.from_jira` returns it for any name outside the six instead of raising, so there is one lookup path. `is_blocked` stays "status is REFINEMENT", so UNKNOWN is not blocked. Board maps have no UNKNOWN entry; display code shows "Unknown (<raw status>)". Alternative: add `IMPLEMENTED` as a seventh status; rejected, because it is not part of the intended workflow and would hide the governance problem.
- **Findings code location:** a new pure module `integrations/jira_findings.py` with `status_finding`, `task_parent_finding`, `wrong_epic_link_findings`; `map_issue` calls them and sorts the result by `(code, field, related_key)` for a stable order.
- **Task without a parent:** computed from the already mapped `parent_key` and kind, so the rule stays identical to the parent rules (Epic Link, or "is child of" a Risk or Issue). Tasks with only "mentions", "clones" or "blocks" links are flagged, as are Tasks with no links.
- **Wrong Epic link:** for kind REQUEST and issue type other than the Epic type, scan links whose direction text matches `issues.request_wrong_epic_phrases` and whose other end has the Epic type; one finding per distinct Epic, naming the Epic and the phrase and suggesting "is caused by". The parent stays unset. A Risk or Issue with no Epic link yields nothing.
- **Tolerant values:** `parse_date` and `parse_timestamp` are wrapped so a failure returns `None` and appends an `INVALID_VALUE` finding naming the field; the same for `parse_sprint`. `seconds_to_days` receives non-numeric input as unknown, with a finding. Absent values remain `None` with no finding.
- **Unusable payload:** only a missing key, `fields`, `project` or `summary` still raises `TicketMappingError`. The status object is optional; a missing one gives UNKNOWN and a finding with raw status absent.
- **Sub-task exclusion:** `issues.excluded_types = ["Sub-task"]` and, in `build_search_jql`, `AND issuetype not in ("Sub-task")` placed after the team clause (omitted when the list is empty). `get_tickets` by key is unchanged, so a Sub-task fetched explicitly is still returned (kind OTHER).
- **Settings:** `issues.request_wrong_epic_phrases = ["is child of", "created by"]`; no setting for the correct phrase because it already exists as `issues.request_parent_phrases`.
- **Docs for later:** `docs/data-quality.md` lists the findings and records the MVP-4 correction flow (preview, confirm, write, re-read to verify; a write-capable credential kept apart from the read-only PAT; changes made under the user's identity).

## Risks / Trade-offs

- [Several existing tests expect IMPLEMENTED to fail and one expects a failure record for it] → Updated deliberately; failure-isolation tests use a payload without a project instead.
- [A Task flagged for having only a "mentions" link may in fact be correctly parented in the team's view] → Per the user's rule; the finding text says which link types were found, and the rule is configuration-light but easy to change.
- [Findings could multiply on the dashboard] → Counts are small (about 61 + 9 + 3 on first measurement); the dashboard change decides presentation.
- [UNKNOWN status hides the raw name from code that ignores it] → The raw name travels with the ticket and in the finding.
