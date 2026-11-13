# Tasks

## 1. Dependencies

- [x] 1.1 Add `httpx` and `truststore` to the project dependencies; verify `uv sync` succeeds on Python 3.15 and `uv run python -c "import httpx, truststore"` works

## 2. Sanitiser

- [x] 2.1 Implement the allow-list sanitiser with synthetic users, generic summaries and panel-only descriptions in `integrations/live_sanitize.py`; verify unit tests for consistent user replacement, dropped unknown fields, removed URLs and avatars, redacted panel bodies with the requester placeholder
- [x] 2.2 Implement the leak scan (Jira host, non-example e-mail addresses, token); verify tests that a leak blocks output and the message does not echo the matched text
- [x] 2.3 Verify that the existing fixtures, once sanitised, map to the same kind, status, parent key, domain, request drivers and effort as before

## 3. Read-only fetcher

- [x] 3.1 Implement the `httpx` fetcher using the truststore SSL context, a bearer header from the credential store and a single GET helper in `integrations/jira_probe.py`; verify tests with `httpx.MockTransport` that every request is GET, the token appears only in the header and TLS verification is not disabled
- [x] 3.2 Map 401, 403, 404, timeouts and connection errors to distinct messages that never include the token; verify a test per case and that other tickets are still processed after a 404
- [x] 3.3 Implement the field-list check comparing configured field IDs with Jira's list; verify tests for a match, a missing ID and a different name

## 4. Report and command

- [x] 4.1 Implement the compatibility report using `map_issue`, including observed link texts, Epic Link shape, sprint format, requester found and expected-type check; verify tests for a mapped Task with parent, an unmapped ticket and a type mismatch
- [x] 4.2 Implement the command `python -m jira_dashboard.integrations.live_check` with key arguments, `--output`, placeholder-URL and missing-token guards and exit codes; verify tests with a mock transport for success, partial failure (exit 1) and the guards
- [x] 4.3 Write `docs/live-data-check.md` (store the PAT, run the command, review the output checklist, how to share the report) and extend `docs/jira-integration.md`; verify the documented command runs against the mock transport in a test

## 5. Quality

- [x] 5.1 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass

## Workflow follow-up

- The live run needs the user's network and PAT: run the command, review the sanitised files, then share the report.
- Based on the report, propose a mapper-correction change before starting `jira-http-client`.
