# Data quality findings

Every ticket the client returns carries `findings`: things in Jira that look wrong and need correcting. Findings are read-only. They are worked out from the one ticket's own data, never change anything in Jira, and never stop a ticket from being returned. They are what the dashboard highlights and what the later correction feature (MVP-4) will act on.

Each finding has a `code`, a `message`, the `field` concerned, an optional `related_key` (another ticket) and a `suggestion` (what the fix would be).

## The findings

| Code | Raised when | Suggested fix |
|---|---|---|
| `NON_STANDARD_STATUS` | the status is not one of NEW, REFINEMENT, BACKLOG, PLANNED, IN_PROGRESS, CLOSED (for example "Implemented") | change the ticket to a standard status |
| `TASK_WITHOUT_PARENT` | a Task has no Epic Link and no "is child of" link to a Risk or Issue | link the Task to its Risk or Issue, or set its Epic Link |
| `REQUEST_WRONG_EPIC_LINK` | a Risk or Issue is linked to an Epic as "is child of" or "created by" | replace the link with "is caused by" |
| `INVALID_VALUE` | a date, timestamp, estimate or sprint cannot be read | correct the value in Jira |

The status of a ticket with a non-standard status is `UNKNOWN`, and the original Jira name stays in `raw_status`, so it can be shown ("Unknown (Implemented)") and corrected.

## What is deliberately not flagged

- An Epic Link on its own is a valid parent for a Task.
- A Risk or Issue with no Epic link at all: some do not originate from a verification assessment.
- A Risk or Issue linked to an Epic as "is caused by" (the correct link).
- Missing estimates, requester, assignee, target dates or sprint. They stay unknown; health checks for them come with MVP-3.
- "mentions" and "is mentioned by" links: they are created by any ticket ID typed in a text field and say nothing about hierarchy.
- Epics, and Sub-tasks (which are left out of the team search; see `issues.excluded_types`).

## Settings

`issues.request_wrong_epic_phrases` (default `is child of`, `created by`) and `issues.excluded_types` (default `Sub-task`); see [configuration.md](configuration.md).

## Planned: correcting findings (MVP-4)

Fixing a finding means writing to Jira, which the read-only dashboard never does. The correction flow follows the "human in the loop" rule:

1. Show the finding and the proposed change (for example the old link and the new "is caused by" link, or the status to move to).
2. The user confirms. Nothing is written without it.
3. Write the change, then read the ticket back from Jira and verify it.
4. Recalculate the findings.

Intended corrections: choose a standard status; replace a wrong Epic link with "is caused by"; add the missing "is child of" link or Epic Link to a Task (the user picks the parent).

Requirements to settle before building it:

- A write-capable credential, stored under its own name and used only by the correction flow, separate from the read-only token.
- Changes made under the user's own identity, so Jira shows who changed what.
- An audit record of every change made.
