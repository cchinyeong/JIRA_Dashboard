# Proposal

## Why

The ticket mapper was built from screenshots and Jira Server conventions, not a real response. MVP-1 builds a dashboard on top of it, so wrong assumptions (link direction texts, the Epic Link value shape, the sprint string, field IDs) would surface late and expensively. A small read-only check against the real VE Jira, run first, replaces those assumptions with facts and gives us real-shaped test fixtures.

## What Changes

- Add a read-only command that fetches the four known tickets (CAE-1513 Epic, CAE-1558 Risk, CAE-1592 Issue, CAE-1628 Task) from the configured Jira using the stored PAT.
- Verify the configured field IDs against Jira's field list.
- Sanitise the responses with an allow-list so that only structural data is kept, and write only the sanitised JSON as fixtures. Raw responses are never written to disk.
- Run the existing mapper on each real payload and print a compatibility report: what mapped, what failed, which link texts and sprint formats were seen, and whether the Task resolves to a parent request.
- Add `httpx` and `truststore` as dependencies; TLS verification stays on and uses the Windows certificate store, so the corporate CA is trusted without disabling checks.
- The check uses GET requests only and never writes to Jira.

## Capabilities

### New Capabilities
- `live-data-sampling`: Read-only retrieval, field verification, sanitisation and compatibility reporting for a small set of real Jira tickets.

### Modified Capabilities

## Impact

- Code: `src/jira_dashboard/integrations/` (sanitiser, read-only fetcher, report, command entry), tests in `tests/unit/`.
- Dependencies: `httpx`, `truststore` (the HTTP stack MVP-1 will reuse).
- Output: sanitised fixtures under `tests/unit/fixtures/live/`.
- Docs: `docs/live-data-check.md`.
- Out of scope: paging, search, the dashboard, the full HTTP client with retries (MVP-1 changes); changing the mapper (done afterwards, based on the report).
