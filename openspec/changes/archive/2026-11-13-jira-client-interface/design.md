# Design

## Context

Models (`Ticket`, `Sprint`, `Domain`, `TicketStatus`), settings (field IDs, working time, requester template, team) and the secrets service already exist (archived changes). `jira_dashboard.integrations` is an empty package. Payload shapes come from Jira Server REST v2 (`/rest/api/2/issue`), observed from ticket CAE-1558: a `{panel:title=...}` description, native time tracking, Sprint as `customfield_10000`, and select-type custom fields.

## Goals / Non-Goals

**Goals:**
- One interface and one mapper through which every Jira payload enters the app.
- Mapper is pure and fully unit-testable without Jira.

**Non-Goals:**
- Any HTTP, auth headers, paging or retry (MVP-1); write-back (MVP-4); changelog-derived actual start; Cloud client.

## Decisions

- **`JiraClient` is an `abc.ABC`** in `integrations/jira_client.py` with `get_ticket(key) -> Ticket` and `search_tickets(*, active_sprints_only=False) -> list[Ticket]`. Query details stay inside implementations, so the interface carries no JQL. Alternative: a `Protocol`; rejected because the spec asks for an interface that cannot be instantiated and ABC gives an immediate error.
- **`JiraOnPremClient(settings, secret_store=None)`** in `integrations/jira_onprem.py`. The constructor raises `JiraNotConfiguredError` naming `jira.base_url` when `settings.jira.is_placeholder`. The read methods raise `NotImplementedError("Remote access arrives in MVP-1")` and neither read secrets nor open connections. `secret_store` is stored for MVP-1.
- **`build_search_jql(active_sprints_only)`** is a public, testable method: `project = "VE_CAE" AND cf[12110] = "Structural Analysis"`, plus `AND sprint in openSprints()`. The `cf[...]` number is derived from the configured field ID. Values are escaped by backslash-escaping `\` and `"`. The project key is quoted too.
- **Mapper** in `integrations/jira_mapping.py`: `map_issue(payload: Mapping, settings: Settings) -> Ticket`, composed of small pure helpers (`seconds_to_days`, `parse_sprint`, `extract_requester`, `parse_timestamp`, `map_user`, `map_kind`, `map_parent`). Failures raise `TicketMappingError(key, reason)` wrapping the underlying cause. The input is only read.
- **Hierarchy:** requests (Epic, Risk, Issue) and tasks, linked by `parent_key`. `TicketKind` (`REQUEST`, `TASK`, `OTHER`) is a new `StrEnum` in `models`, and `Ticket` gains `kind: TicketKind = OTHER` and `parent_key: str | None = None` as defaulted fields, so existing construction still works. Settings gain an `issues` section (`request_types`, `task_types`, overlap rejected, `parent_link_phrases`) and `fields.epic_link`, defaulting to `customfield_10001` and the phrases `is child of` and `is caused by`. Alternative: a nested parent object; rejected to keep models flat and avoid cycles.
- **Parent mapping:** the Epic Link value (a key string on Jira Server) wins; otherwise the issue links are scanned. Jira shows a link from one side only: a link with `inwardIssue` reads as `type.inward` on this ticket, and one with `outwardIssue` reads as `type.outward`. A link qualifies when that text matches a configured phrase (case-insensitive) and the other end's issue type is Risk or Issue; candidates are sorted by key and the first is used. Only tasks get a parent. Matching on the visible phrase avoids needing link type IDs, which are not shown in the Jira UI.
- **Requester stays per ticket** in the pure mapper. Showing a Task's requester from its parent is a later service-layer join, because the mapper sees one payload at a time.
- **Interface:** `get_tickets(keys)` is added so the service layer can load the parent requests of sprint Tasks in one call; the skeleton raises not-implemented for it too. The fields requested later must include `issuetype`, `issuelinks` and the Epic Link field.
- **Fixtures:** `issue_cae_1558.json` (Risk), plus a Task linked to an Epic through Epic Link and a Task linked to a Risk through an issue link. All invented, no real hosts.
- **Effort:** `seconds / (hours_per_day * 3600)`; `None` stays `None`.
- **Sprint parsing:** a field may be a list. Items are either dicts (`id`, `name`, `state`, `startDate`, `endDate`) or legacy strings `...Sprint@hash[id=12,rapidViewId=3,state=ACTIVE,name=...,startDate=...,endDate=...]`. The legacy body is parsed with a regex that splits on `,key=` boundaries, because names contain spaces, parentheses and possibly commas. Pick the `ACTIVE` sprint, else the one with the highest id. `<null>` values become `None`; dates are cut to calendar dates.
- **Requester:** regex `\{panel:[^}]*title=<escaped configured title>[^}]*\}(.*?)\{panel\}` with DOTALL; take the first non-empty line, strip whitespace and trailing `.`, `,`, `;`, `:`. Case-insensitive comparison against placeholders; empty gives `None`. A formatted result such as `[~username]` is kept as-is for MVP-6.
- **Select fields:** Simulation Type is `{"value": ...}`; Components are a list of `{"name": ...}`.
- **Test fixture:** `tests/unit/fixtures/issue_cae_1558.json`, modelled on the screenshot, with invented user data limited to what the screenshot showed, and no real tokens or internal URLs (host `https://jira.example.com`).

## Risks / Trade-offs

- [Payload shapes inferred from screenshots, not a real response] → MVP-1 must validate the mapper against live data first; unknown shapes fail loudly with the ticket key rather than silently.
- [Link phrases beyond "is child of" and "is caused by" may exist] → Configurable list; Tasks linked by an unlisted phrase get no parent and are logged by the service layer later. MVP-1 should list the phrases found on real Tasks.
- [Link direction text could differ from the UI wording, for example by language or version] → MVP-1 validates against a real payload.
- [Legacy sprint string is brittle] → Parser is isolated, tested with names containing commas and parentheses, and the dict form is also supported.
- [Raising on an unsupported status fails that ticket] → The error carries the key, so callers can skip and log it.
- [JQL built by string] → Quoting/escaping helper with a test for a quote in the team name; no user input reaches it in MVP-0.
