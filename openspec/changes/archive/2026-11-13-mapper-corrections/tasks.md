# Tasks

## 1. Configuration

- [x] 1.1 Replace `issues.parent_link_phrases` with `issues.task_parent_phrases` (default `is child of`), `issues.request_parent_phrases` (default `is caused by`) and `issues.epic_type` (default `Epic`) in settings and `default.toml`, and set `jira.project_key` to `CAE`; verify tests for the new defaults, that `mentions` is not a default, that the old key is rejected with its name, and update existing config tests that referenced `VE_CAE`
- [x] 1.2 Update `docs/configuration.md` for the new keys and the project key; verify the documented override example loads in a test

## 2. Parent mapping

- [x] 2.1 Rewrite `map_parent` with per-kind rules (task: Epic Link then "is child of" to Risk or Issue; Risk or Issue: "is caused by" to Epic; Epic: none; lowest key wins; targets derived from settings); verify unit tests for each scenario in the spec, including a task linked to another Task or an Epic, and a Risk caused by an Epic
- [x] 2.2 Add the regression tests for "mentions": the real CAE-1558 link shapes (outward "mentions" two Issues, inward "is mentioned by" a Task) and a Task that "mentions" a Risk; verify none yields a parent

## 3. Query

- [x] 3.1 Use the project key `CAE` in the query and rename the sprint option to `in_sprints_only` in the interface, the skeleton and `build_search_jql`, adding `sprint in (openSprints(), futureSprints())`; verify updated unit tests for project and team scope, sprint scope and quote escaping

## 4. Real-shape regression and docs

- [x] 4.1 Add `tests/unit/test_live_fixtures.py` mapping every file in `tests/unit/fixtures/live/` and asserting the observed kinds, statuses, request drivers and parents (CAE-1628 parent CAE-1513, the Epic, Risk and Issue without parent), skipping when the folder is empty; verify it passes with the current fixtures and skips without them
- [x] 4.2 Update `docs/jira-integration.md` (hierarchy rules, "mentions" excluded, future sprints, project key); verify it matches the specs
- [x] 4.3 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass

## Workflow follow-up

- Review and commit the sanitised fixtures in `tests/unit/fixtures/live/`.
- Archive this change, then propose `jira-http-client`.
