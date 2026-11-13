# Tasks

## 1. Models

- [x] 1.1 Add `TicketStatus.UNKNOWN` and make `TicketStatus.from_jira` return it for names outside the six; verify tests for the six names, case and spacing, "IMPLEMENTED" giving UNKNOWN without an error, and that `is_blocked` is false for UNKNOWN (updating the existing test that expected an error)
- [x] 1.2 Add `FindingCode` and the frozen `Finding`, and `raw_status` and `findings` on `Ticket`; verify tests for defaults, the raw status being kept, and that assigning findings to a ticket fails

## 2. Settings

- [x] 2.1 Add `issues.excluded_types` (default `Sub-task`) and `issues.request_wrong_epic_phrases` (defaults `is child of`, `created by`) to settings and `default.toml`, and document them in `docs/configuration.md`; verify tests for the defaults and that `is caused by` is not a wrong phrase

## 3. Tolerant mapping

- [x] 3.1 Make the mapper keep the raw status and map unsupported statuses to UNKNOWN, requiring only key, fields, project and summary; verify tests for "Implemented" mapping to UNKNOWN with its raw name, a missing project raising a mapping error naming the key, and a payload without priority, assignee, sprint or estimates mapping with unknown values (updating the mapping tests that expected an error for IMPLEMENTED)
- [x] 3.2 Make dates, timestamps and sprint lenient: an unreadable value becomes unknown with an `INVALID_VALUE` finding naming the field and the ticket is still returned; verify tests for an invalid target end, an invalid created timestamp and an unreadable sprint, each mapping the other fields

## 4. Findings

- [x] 4.1 Add `integrations/jira_findings.py` with the non-standard status, Task-without-parent and wrong-Epic-link rules, attach the findings in `map_issue` in a stable order; verify tests for each scenario in the spec, including an Epic Link alone, "is child of" a Risk, only "mentions" or "clones" links, no links, a Risk with no Epic link, "is caused by" an Epic, "is child of" and "created by" an Epic, and identical output when mapped twice
- [x] 4.2 Extend the live-fixture regression tests: the four live tickets give no findings except as expected for their shapes (CAE-1628 has an Epic Link so no parent finding; the Risk with only "mentions" links has none); verify they pass with the fixtures and skip without them

## 5. Query

- [x] 5.1 Add the excluded issue types to `build_search_jql` (omitted when empty) and update the query tests and failure-isolation tests (the unmappable example is now a payload without a project); verify that explicit key retrieval returns a Sub-task

## 6. Docs and quality

- [x] 6.1 Write `docs/data-quality.md` (the four findings with their rules, what is deliberately not flagged, how Sub-tasks and the unknown status are handled, and the planned MVP-4 correction flow and credential separation) and update `docs/jira-integration.md`; verify they match the specs
- [x] 6.2 Re-run the read-only live search and confirm that "Implemented" tickets now appear as UNKNOWN with a finding, Sub-tasks are gone, and the finding counts match expectations (about 61 task, about 9 wrong-link, 3 status); verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass

## Workflow follow-up

- Show the findings in the dashboard UI (next MVP-1 changes).
- Build the correction flow in MVP-4 (write-capable credential, preview, confirm, write, verify).
