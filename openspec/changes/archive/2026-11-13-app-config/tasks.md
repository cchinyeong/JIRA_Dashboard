# Tasks

## 1. Settings schema

- [x] 1.1 Add frozen, `extra="forbid"` section models in `config/settings.py` for jira (HTTPS-only URL, project key, team filter, timeout), field mapping, working time (positive values), requester template, board maps, risk, app and logging; verify unit tests cover invalid URL, zero hours per day and bad log level
- [x] 1.2 Add `jira_dashboard/config/default.toml` with the confirmed VE values and placeholders (base URL on `.invalid`, actual-start unset); verify a test loads defaults and checks project key, team, field IDs, 8 h/day, 5 d/week, requester title and board labels

## 2. Loading and overrides

- [x] 2.1 Implement `Settings` source order (env, local file, packaged defaults) and `get_settings()`; verify tests for local-file override, env-over-file priority and `JIRA_DASHBOARD_CONFIG_FILE`
- [x] 2.2 Verify unknown keys (including `token` and `password`) fail loading with the key named, and that assigning to a loaded setting raises; add tests
- [x] 2.3 Add an `is_placeholder` check for the Jira base URL; verify with tests for default and overridden URLs

## 3. Quality and docs

- [x] 3.1 Export the public names from `config/__init__.py`; verify `from jira_dashboard.config import get_settings` works in a test
- [x] 3.2 Document layering, environment-variable examples, placeholders and provisional values in `docs/configuration.md`; verify the example override loads in a test
- [x] 3.3 Verify `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` all pass
