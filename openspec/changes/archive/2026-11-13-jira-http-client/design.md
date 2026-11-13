# Design

## Context

The live check produced `jira_probe.py`: an `httpx` client with the Windows trust store, bearer auth, a single GET helper, and classified errors (`ProbeError`). `JiraOnPremClient` is a skeleton with a URL guard and a team query builder; the mapper handles real payloads (archived `mapper-corrections`). Observed scale: roughly 170 open tickets and hundreds of closed ones, with project key `CAE` and a team custom field. Per-field tolerance and UNKNOWN handling come in the next change.

## Goals / Non-Goals

**Goals:**
- One HTTP layer used by both the live check and the client.
- Reliable retrieval of the VE team's tickets with bounded load.
- A failing ticket never hides the others; a failing request is reported clearly.

**Non-Goals:**
- Tolerant field mapping, caching or persistence, background refresh, the service layer, the GUI, writing to Jira.

## Decisions

- **`jira_probe.py` becomes `jira_http.py`**, `JiraProbe` becomes `JiraHttp`, `ProbeError` becomes `JiraApiError(kind, message)`. `check_fields` and `requested_fields` move with it. The live check imports the new names. Alternative: keep the probe and add a second HTTP class; rejected as duplicated TLS, auth and error code.
- **Single request path:** `JiraHttp._get(path, params)` is the only method that touches the network and only calls `Client.get`. A test routes every operation through a recording transport and asserts the method.
- **Retry:** attempts = 1 + `jira.max_retries`. Retryable: timeout, connection error, HTTP 429, 502, 503, 504. Delay `0.5 * 2**attempt` seconds, capped at 5, taken from an injectable `sleep` callable so tests do not wait. The certificate error is not retried (it will not fix itself). The last cause becomes the raised error.
- **Paged search:** `JiraHttp.search(jql, fields)` is a generator using `GET /rest/api/2/search` with `startAt`, `maxResults=jira.page_size` and `fields`; it stops when `startAt` reaches `total` or a page is empty. Alternative: ask for a huge page; rejected because Jira caps it.
- **Batch type:** `TicketBatch(tickets: list[Ticket], failures: list[TicketFailure])` and `TicketFailure(key, reason)` are frozen dataclasses in `integrations/jira_client.py`. `get_ticket` still returns a `Ticket` and raises `TicketMappingError` or `JiraApiError`. Alternative: raise on the first mapping error; rejected because one malformed ticket would blank the dashboard. A request-level failure still raises, because a partial batch from a failing request would silently drop tickets.
- **Fetch by keys:** keys are validated with the existing key pattern, de-duplicated, and requested as `key in (...)` JQL in chunks of 50 (search endpoint, same paging). Absent keys are not failures: Jira omits issues the user cannot see or that do not exist, which the caller sees as absent.
- **Team matched by numeric ID (found on the first live run):** the Team field (`customfield_12110`) is an object `{id, name}` (a team picker), and `cf[12110] = "Structural Analysis"` returned zero tickets while `cf[12110] = 400` returned the team's tickets. Settings gain `jira.team_id` (default 400, positive integer); the query uses `cf[12110] = <id>` and no quoting is needed because it is an integer. `jira.team` stays as a human-readable label. Alternative: look the ID up from the name at runtime; rejected, because it needs another request and an unknown API for the team picker.
- **Look-back JQL:** `AND (status != "Closed" OR updated >= -30d) ORDER BY key ASC`, with the day count from settings and the status name from `TicketStatus.CLOSED`. The sprint filter from the previous change is kept and ordered before the look-back.
- **Settings:** `jira.page_size` (default 100, 1 to 1000), `jira.max_retries` (default 2, at least 0), `jira.closed_lookback_days` (default 30, at least 0), validated by the existing `JiraSettings`.
- **Token timing:** `JiraOnPremClient` builds `JiraHttp` and reads the token on first request via `get_secret(JIRA_PAT, secret_store)`, so constructing the client (for example in tests or at app start) stays free of credential access. `MissingSecretError` propagates unchanged because its message already explains how to store the token.
- **Logging:** the HTTP layer logs `GET <path> -> <status> in <ms> ms` at debug level and retry notices at warning level, never headers or bodies. The redaction filter remains the second defence.
- **Testing:** `httpx.MockTransport` with the sanitised live fixtures as issue payloads; the injected `sleep` records delays.

## Risks / Trade-offs

- [The team ID is specific to this Jira instance] → It is configuration with a documented default; the live check shows it with the field check if it ever changes.
- [The `/search` response shape or paging differs on this Jira version] → Verified on the first live run: paging over 1,533 issues and the `issues`/`total` envelope work.
- [A very large team filter could still return thousands of tickets] → Paged retrieval bounds each request; the look-back bounds the closed set. A hard cap can be added if needed.
- [Retries may delay failure feedback] → At most two retries with short capped delays.
- [Changing return types of two interface methods] → Only the skeleton and a fake in tests implement them today.
- [Missing keys are silently omitted] → Documented; the service layer can report orphaned parents.
- [JQL built from strings] → Keys pass a strict pattern, other values reuse the existing quoting helper, and the look-back is an integer from validated settings.
