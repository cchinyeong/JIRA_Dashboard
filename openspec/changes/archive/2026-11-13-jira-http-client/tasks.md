# Tasks

## 1. Settings

- [x] 1.1 Add `jira.page_size`, `jira.max_retries` and `jira.closed_lookback_days` with validation and defaults in settings and `default.toml`, and document them in `docs/configuration.md`; verify tests for defaults, page size 0 and 5000 rejected, and negative retries and look-back rejected

- [x] 1.2 Add `jira.team_id` (positive integer, default 400) to settings and `default.toml` and document it in `docs/configuration.md`; verify tests for the default, and that 0 and a negative value are rejected

## 2. Shared HTTP layer

- [x] 2.1 Rename `jira_probe.py` to `jira_http.py` (`JiraHttp`, `JiraApiError`) and update the live check and its tests; verify the existing probe and live-check tests pass under the new names
- [x] 2.2 Add bounded retry with capped exponential delay and an injectable sleep to `_get`; verify tests for recovery after one 503, exhaustion after 1 + max retries attempts, 401 and 404 not retried, and the certificate error not retried
- [x] 2.3 Add paged `search` (`startAt`, `maxResults`, stop on total or empty page); verify tests for 250 issues over three requests, an empty page ending the search, and that no request uses a method other than GET
- [x] 2.4 Add safe request logging (method, path, status, duration; retry warnings); verify a test with debug logging that no log record contains the token or a response body

## 3. Client

- [x] 3.1 Add `TicketBatch` and `TicketFailure` and change `get_tickets` and `search_tickets` in the interface to return a batch; verify a fake subclass test
- [x] 3.2 Implement `get_ticket` and `get_tickets` in `JiraOnPremClient` (key validation, de-duplication, chunks of 50, missing keys omitted, lazy token read); verify tests for a found ticket, a 404 naming the key, chunking of 120 keys into three requests, an invalid key making no request, a missing token, and no credential access at construction
- [x] 3.3 Implement `search_tickets` with the closed-ticket look-back, key ordering and per-ticket failure isolation, extending `build_search_jql`; verify tests for the query text with defaults and a 7-day look-back, sprint scope plus look-back, one unmappable ticket giving a failure record while the others map, and an authentication error raising without a partial batch
- [x] 3.4 Verify an end-to-end test through a mock transport that uses the sanitised live fixtures for a search of a Task and its Epic and checks kinds, parents and that every request is GET

- [x] 3.5 Make `build_search_jql` match the team by `cf[12110] = <team_id>` instead of the quoted name, and update the query tests (default text, 7-day look-back, sprint scope, a team name containing a quote leaving no trace in the query) and the end-to-end test; verify `uv run pytest` passes

## 4. Docs and quality

- [x] 4.1 Update `docs/jira-integration.md` (client behaviour, look-back, retries, failure records, what the first live run must confirm about the search response); verify it matches the specs
- [x] 4.2 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass

- [x] 4.3 Re-run the read-only live search through the client and confirm it returns the team's tickets (non-zero, about the open count plus recent closed), that failures are few, and that every ticket kind and parent rule behaves as expected; update `docs/jira-integration.md` with what was confirmed

## Workflow follow-up

- First live run done: connection, TLS, authentication, paging over 1,533 issues, `futureSprints()` and `cf[12110]` were confirmed; the team had to be matched by ID.
- Next change: tolerant per-field mapping with UNKNOWN handling.
