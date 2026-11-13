# Jira integration

All Jira access goes through `jira_dashboard.integrations.JiraClient`. It returns internal models only; nothing outside `integrations` sees Jira payloads. `JiraOnPremClient` implements it for Jira Server. A `JiraCloudClient` can replace it later without changes elsewhere.

## Client behaviour (MVP-1)

- Construction fails with `JiraNotConfiguredError` while `jira.base_url` is still the placeholder. The token is read from Credential Manager on the first request, not at construction; a missing token raises an error that explains how to store it (`docs/security.md`).
- `get_ticket(key)` returns a `Ticket`, or raises `JiraApiError` (kind `not_found` names the key) or `TicketMappingError`.
- `get_tickets(keys)` validates and de-duplicates keys and fetches them in chunks of 50. Keys Jira does not return are simply absent.
- `search_tickets(in_sprints_only=False)` runs the team query, fully paged. Both multi-ticket methods return a `TicketBatch`: the tickets that mapped, plus a `TicketFailure(key, reason)` for each issue that could not be mapped, so one bad ticket never hides the rest. A failing request (authentication, network) raises instead; no partial batch is returned.
- `JiraHttp` is the only code that touches the network: GET requests only, bearer token in the header only, TLS verified against the Windows certificate store, errors classified as `auth`, `not_found`, `timeout`, `connection`, `tls` or `http`. Timeouts, connection errors and HTTP 429/502/503/504 are retried up to `jira.max_retries` times with growing delays (0.5 s doubling, capped at 5 s). Logs contain method, path, status and duration only.
- `map_issue(payload, settings)` converts a Jira Server issue (REST v2 JSON) into a `Ticket`. It is pure. Only an unusable payload (no key, fields, project or summary) raises `TicketMappingError`; everything else maps as far as possible: an unreadable date becomes unknown with a finding, and a non-standard status becomes `UNKNOWN` with its raw name kept. See [data-quality.md](data-quality.md).

## Query scope

`build_search_jql()` gives `project = "CAE" AND cf[12110] = 400 AND (status != "Closed" OR updated >= -30d) ORDER BY key ASC` (`CAE` is the project key; `VE_CAE` is only its name; 400 is the team's ID, because the Team field is a team picker that Jira matches by ID, not name). Open tickets are always included; closed tickets only when updated within `jira.closed_lookback_days`. `build_search_jql(in_sprints_only=True)` adds `AND sprint in (openSprints(), futureSprints())` before the look-back, because planned Tasks sit in future sprints. Values are quoted and escaped, and results are ordered by key so paging is stable.

## Ticket hierarchy

Epic, Risk and Issue tickets are requests (`TicketKind.REQUEST`); Tasks (`TicketKind.TASK`) are the sprint work. Parents are set per kind, using the link text Jira shows on the ticket:

| Ticket | Parent | How |
|---|---|---|
| Task | Epic | Epic Link field (`customfield_10001`); these Epics are not Jira containers |
| Task | Risk or Issue | link `is child of` (`issues.task_parent_phrases`) |
| Risk or Issue | Epic | link `is caused by` (`issues.request_parent_phrases`) |
| Epic | none | |

"mentions" and "is mentioned by" links are never used: any ticket ID typed in a free-text field creates one (the real Risk CAE-1558 has three). If several links qualify, the lowest key is used. Parents and children share a project on Jira on-prem; Jira Cloud can differ and is handled in MVP-9.

A ticket's requester is not inherited in the mapper; each ticket's own description panel is read.

## Payload quirks handled

- Effort arrives in seconds and becomes days (`working_time.hours_per_day`). Tickets without an estimate map to unknown.
- Sprint is a list of legacy strings (`...Sprint@hash[id=12,state=ACTIVE,name=...]`) or structured objects; the active sprint is chosen, otherwise the highest id, so a future sprint beats a closed one.
- Domain comes from the Simulation Type select field, request drivers from Components.
- Timestamps carry offsets such as `+0800`.

## Verified against the real Jira

The [live data check](live-data-check.md) confirmed the field IDs, the Epic Link value (a key string), the legacy sprint string, and the link texts above on four real tickets. Sanitised copies live in `tests/unit/fixtures/live/` and are regression-tested. Not yet seen on real data: a Risk or Issue linked "is caused by" to an Epic; it is covered by a synthetic test from the stated rule.

## Confirmed on the first live run of the client (13 Nov 2026)

- Connection, certificate trust (Windows store), PAT authentication and paging work: a project-wide query returned 1,533 issues over 16 pages and the `issues` / `total` envelope matched.
- `openSprints()`, `futureSprints()`, `ORDER BY key` and the `cf[12110]` reference are accepted.
- The Team field is a team picker (`{id, name}`) that must be matched by numeric ID: `cf[12110] = 400` works, the name matches nothing. This is why `jira.team_id` exists.
- With the default query (open plus closed in the last 30 days) the client returned 352 tickets and 3 failure records; with `in_sprints_only` it returned 72 tickets and no failures.

## Data observations for later changes

These came from the same run and are not bugs in the client:

- **Status "Implemented"** exists on 3 tickets. It is not an official status, so those tickets appear with status `UNKNOWN` and a `NON_STANDARD_STATUS` finding.
- **Sub-tasks** exist (2 in the sample); they are excluded from the team search (`issues.excluded_types`).
- **Tasks without a parent:** 61 of 141. Most have only "mentions", "clones" or "blocks" links, which are deliberately not used; 7 have no links at all. Each gets a `TASK_WITHOUT_PARENT` finding.
- **Risks and Issues linked to an Epic wrongly:** some use "is child of" (4 seen) or "created by" (5 seen) instead of "is caused by"; each gets a `REQUEST_WRONG_EPIC_LINK` finding. A Risk or Issue with no Epic link is not flagged.
- **Parents are not in a sprint-only search:** none of the sprint tasks' parents (Epic, Risk, Issue) were in the sprint result, which is why `get_tickets` exists for loading them.
- **Estimates and requesters:** 95 of 352 tickets have an estimate; 254 have a requester.
