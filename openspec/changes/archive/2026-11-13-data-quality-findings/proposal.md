# Proposal

## Why

The first live run showed that VE Jira data is not always clean: three tickets use a status ("Implemented") outside the official workflow, 61 of 141 Tasks have no parent, some Risks and Issues are linked to an Epic with the wrong link text, and Sub-tasks appear that do not belong on this dashboard. Today a non-standard status turns a ticket into a failure record, so it vanishes from the dashboard exactly when it needs attention. The dashboard should instead show every ticket and highlight what needs correcting. The correction itself is Jira write-back (MVP-4) and is out of scope here; this change builds the read-only detection that feeds it.

## What Changes

- Add `data-quality-findings`: each ticket carries zero or more findings (code, message, related field or ticket) derived from its own payload. Four finding types:
  - non-standard status (for example "Implemented"),
  - Task without a parent (no Epic Link and no "is child of" link),
  - Risk or Issue linked to an Epic by "is child of" or "created by" instead of "is caused by",
  - invalid value (an unreadable date, timestamp or sprint), kept as unknown.
- The status model gains `UNKNOWN` and every ticket keeps its raw Jira status name; an unsupported status no longer fails the ticket.
- Mapping becomes tolerant: only an unusable payload (no key, fields, project or summary) is a failure; everything else is mapped as far as possible.
- Sub-tasks are excluded from the team search through a configurable list of excluded issue types.
- New settings: excluded issue types and the link phrases that count as a wrong Epic link.
- Documentation of the findings and of the planned MVP-4 correction flow.

A Risk or Issue with no Epic link is not flagged (some do not originate from a verification assessment), and an Epic Link alone is a valid parent for a Task.

## Capabilities

### New Capabilities
- `data-quality-findings`: Detection and representation of data-quality problems on tickets, read-only.

### Modified Capabilities
- `ticket-domain-model`: adds the unknown status, the raw status name, and findings on tickets.
- `jira-ticket-mapping`: unsupported statuses map to unknown; adds the unusable-payload rule.
- `app-configuration`: adds data-quality settings.
- `jira-client-abstraction`: the team search excludes configured issue types; the failure-isolation example changes because an unsupported status no longer fails a ticket.

## Impact

- Code: `models` (status, finding, ticket), `integrations/jira_mapping.py`, `integrations/jira_onprem.py`, `config/settings.py`, `default.toml`, and their tests (several existing tests expected "IMPLEMENTED" to fail and change).
- Behaviour: tickets with a non-standard status now appear (as UNKNOWN) instead of being failure records.
- Docs: new `docs/data-quality.md`; updates to `docs/jira-integration.md` and `docs/configuration.md`.
- Out of scope: any write to Jira and the correction UI (MVP-4), the dashboard display of findings (MVP-1 UI), cross-ticket checks, missing-estimate or stale-data health (MVP-3).
