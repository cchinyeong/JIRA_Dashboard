# Proposal

## Why

MVP-1 acceptance needs the app to connect to Jira on-premises, retrieve the VE tickets, convert them to internal models and stay read-only. The `JiraOnPremClient` is still a skeleton, and the only working HTTP code is the small probe built for the live data check. The real client must add paging, the closed-ticket look-back (hundreds of closed tickets should not be reloaded every refresh), retry of transient failures, clear error handling and per-ticket failure isolation, without changing what the rest of the app sees.

## What Changes

- Turn the live-check probe into a shared read-only HTTP layer (`JiraHttp`) with GET-only access, PAT bearer authentication, TLS verification against the Windows certificate store, error classification (authentication, not found, timeout, connection, certificate, other HTTP), bounded retries with backoff for transient failures, and paged search.
- Implement `JiraOnPremClient.get_ticket`, `get_tickets` and `search_tickets` on top of it, mapping each issue with the existing mapper.
- Search covers open tickets plus tickets updated within a configurable look-back (default 30 days) and returns stably ordered, fully paged results.
- `get_tickets` and `search_tickets` return a batch of tickets plus per-ticket failure records, so one unmappable or invalid ticket never hides the others.
- The PAT is read from the credential store on first use; the constructor keeps its URL guard.
- New retrieval settings: page size, maximum retries, closed-ticket look-back days.
- The team query matches the team by its numeric ID (`jira.team_id`, default 400). The first live run showed the team field is an object with an ID and that a name-based query matches nothing.
- The live data check switches to the shared HTTP layer (no behaviour change).

## Capabilities

### New Capabilities
- `jira-http-access`: Read-only, authenticated, TLS-verified, retrying and paged HTTP access to Jira Server with classified errors.

### Modified Capabilities
- `jira-client-abstraction`: the interface returns ticket batches with failure records; adds look-back, batch fetch and failure isolation; the skeleton "no network calls" requirement is removed.
- `app-configuration`: adds retrieval settings.

## Impact

- Code: `integrations/jira_probe.py` becomes `jira_http.py`, `jira_client.py`, `jira_onprem.py`, `live_check.py`, `config/settings.py`, `config/default.toml`, and their tests.
- API: `get_tickets` and `search_tickets` now return `TicketBatch` instead of a list; the sprint option name from the previous change is kept.
- Dependencies: none new (`httpx`, `truststore` already added).
- Docs: `docs/jira-integration.md`, `docs/configuration.md`.
- Out of scope: tolerant per-field mapping and UNKNOWN handling (next change), the ticket service, caching, the GUI and first-run setup, any write access.
