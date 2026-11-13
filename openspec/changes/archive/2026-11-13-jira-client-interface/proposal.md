# Proposal

## Why

The final MVP-0 criteria are a `JiraClient` interface, a `JiraOnPremClient` skeleton, and an app that depends on internal models rather than Jira payloads. Exploration established the on-prem payload quirks the application must absorb in one place: effort arrives in seconds, the sprint field is a legacy string, the requester is hidden in a wiki-markup description panel, and the domain and request drivers come from a custom select field and Components. Isolating this keeps the later Jira Cloud migration (MVP-9) a client swap.

## What Changes

- Add an abstract `JiraClient` in `jira_dashboard.integrations` whose methods return internal `Ticket` models only.
- Add a `JiraOnPremClient` skeleton: validates configuration, builds the team-scoped query, and exposes the planned operations, but makes no network calls yet (MVP-1 adds them).
- Add a pure payload-to-model mapper for Jira Server REST payloads, using the configured field IDs:
  - Seconds to days using the configured working time.
  - Legacy and dictionary sprint formats.
  - Simulation Type to `Domain`, Components to request drivers.
  - Requester extracted from the configured description panel, with placeholder text treated as no requester.
  - Dates, timestamps, users and the issue URL.
  - Ticket kind (request or task) from the issue type, and a task's parent request from the Epic Link or from an issue link to a Risk or Issue.
- Reflect the VE ticket hierarchy: Epic, Risk and Issue tickets are requests (delivery drivers Verification, Risk and Issue); Tasks are the sprint work items and belong to one request. An Epic here is not a Jira container, so Tasks reach it through the Epic Link field (`customfield_10001`), and Risk/Issue through issue links matched by their visible phrase ("is child of", "is caused by").
- Add `TicketKind` and `parent_key` to the ticket model, and issue hierarchy settings to configuration.
- Mapping failures raise a specific error that names the ticket key.
- The client refuses to be created while the Jira base URL is still the placeholder.

## Capabilities

### New Capabilities
- `jira-client-abstraction`: The Jira-agnostic client interface and the on-prem client skeleton, including configuration guard and team-scoped query building.
- `jira-ticket-mapping`: Conversion of Jira Server issue payloads into internal ticket models.

### Modified Capabilities
- `ticket-domain-model`: adds ticket kind and parent reference.
- `app-configuration`: adds issue hierarchy settings.

## Impact

- Code: `src/jira_dashboard/integrations/**`, small additions to `models` and `config`, tests in `tests/unit/` with sample payloads modelled on CAE-1558 and on a Task linked to an Epic.
- Dependencies: none new.
- Docs: `docs/jira-integration.md`.
- Out of scope: HTTP requests, authentication headers, paging and retries (MVP-1), write-back (MVP-4), actual-start from changelog, user identity resolution (MVP-6), `JiraCloudClient` (MVP-9).
