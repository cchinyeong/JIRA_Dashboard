# Design

## Context

The mapper, client skeleton, secrets service and settings exist (archived MVP-0 changes). There is no HTTP code yet. The VE Jira is on an internal host with a corporate certificate authority, and the PAT lives in Windows Credential Manager. `httpx` 0.28 and `truststore` 0.10 resolve for Python 3.15. This change is also the first HTTP code, so its fetcher is meant to be reusable by MVP-1.

## Goals / Non-Goals

**Goals:**
- A command the user runs on their machine that confirms or corrects the mapper's assumptions.
- Fixtures that are real in shape and safe to commit.

**Non-Goals:**
- Paging, search, retries, caching, or a full client (`jira-http-client` in MVP-1).
- Fixing the mapper; the report drives a follow-up change.

## Decisions

- **Entry point** `python -m jira_dashboard.integrations.live_check [KEYS...] [--output DIR]`, run with `uv run`. Default keys: CAE-1513, CAE-1558, CAE-1592, CAE-1628. Default output `tests/unit/fixtures/live/`.
- **HTTP stack:** `httpx.Client` with `verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)`, so the Windows certificate store (including the corporate CA) is used. No `verify=False` code path exists. Alternative: `requests` plus a CA bundle path; rejected because it needs an exported certificate file.
- **Read-only by construction:** the fetcher class exposes one private `_get` helper, and nothing else issues requests. A unit test records every request through `httpx.MockTransport` and asserts the method is GET.
- **Auth:** `Authorization: Bearer <PAT>` from `get_secret(JIRA_PAT)`. The redaction registry already masks it; the check also never formats the header into messages. Errors are built from status codes and exception classes, not from request/response dumps.
- **Minimal retrieval:** `GET /rest/api/2/issue/{key}?fields=<configured field IDs + summary,description,status,issuetype,priority,assignee,reporter,created,updated,project,issuelinks>`, and one `GET /rest/api/2/field`. The field check compares each configured ID with the returned `id` and logs the returned `name` next to the expected concept.
- **Sanitiser (allow-list, not deny-list):** build a new payload from the allow-listed paths only, so unknown or new fields cannot leak. Users map to `user-1`, `user-2` in order of appearance with `User 1` display names and `user-N@example.com` addresses. Summary becomes `Sample ticket <KEY>`. The description keeps each `{panel:title=...}` header, replaces panel bodies with `<redacted>`, and replaces the requester panel body with `Person A.` (trailing period kept to exercise the parser). Self URLs, avatars, watchers and everything else are dropped. Ticket keys, link texts, linked keys and types, dates, estimates, sprint values, Epic Link, components and Simulation Type are kept. Sprint names are kept because they encode only week numbers.
- **Leak scan before writing:** search the serialised output for the Jira host, any `@` e-mail pattern except `example.com`, and the token. Any hit aborts the write and is reported without echoing the matched text.
- **Raw responses stay in memory;** nothing but the sanitised JSON is written.
- **Report:** plain text to the console; one block per ticket plus a summary of observed link texts, Epic Link shape (`str`, `dict`, `None`), sprint format (`legacy`, `structured`, `none`) and field ID findings. It uses the existing `map_issue` and prints the mapped values or the `TicketMappingError`.
- **Exit codes:** 0 when every ticket was retrieved, 1 when any failed or the check could not start. Mapper failures do not change the exit code, because reporting them is the purpose.
- **Expected shapes:** the four keys carry expectations from the user (Epic, Risk, Issue, Task); the report flags a ticket whose issue type differs.
- **Dependencies:** `httpx` and `truststore` are added to the project; tests use `httpx.MockTransport` with the existing synthetic fixtures standing in for "raw" payloads.

## Risks / Trade-offs

- [Allow-list may drop a field the mapper later needs] → The report shows what the mapper could not find; add to the allow-list and rerun.
- [Sanitised output could still carry something sensitive, for example a sprint or component name] → Leak scan plus a documented manual review before committing; the user reviews the files before they are added to the repository.
- [truststore on Windows relies on the system store] → Matches the corporate setup; failure surfaces as a clear TLS error message.
- [A PAT with write rights would make a bug dangerous] → GET-only by construction, a test, and guidance to use a read-only account.
- [Four tickets may not show every variant] → Acceptable for a first check; the command accepts other keys.
