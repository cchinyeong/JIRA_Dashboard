# Proposal

## Why

MVP-0 needs a maintainable base before models, config, secrets and the Jira client are added. The repo is an untouched `uv` scaffold: Python floor is 3.9, there is no package layout, no test framework and no lint setup. Fixing this first lets the four following MVP-0 changes (`domain-models`, `app-config`, `logging-secrets`, `jira-client-interface`) land on a stable footing.

## What Changes

- Raise the Python floor to 3.15 (`.python-version` and `requires-python`); 3.15.2 is installed and the planned dependencies install on it.
- Add runtime dependencies needed by later MVP-0 changes: `pydantic-settings`, `keyring`.
- Add a dev dependency group: `pytest`, `ruff`.
- Create the package layout under `src/jira_dashboard/`: `models`, `services`, `integrations`, `config`, `utils`. Only folders MVP-0 needs; no `skills`, `agents`, `workflows`, `ui` or `database` yet.
- Create `tests/unit` and `tests/integration` plus `docs/`; `tests/end_to_end` is deferred until there is something to test end to end.
- Configure pytest and ruff in `pyproject.toml`.
- Extend `.gitignore` for secrets and local config (`.env`, `*.local.toml`, `.pytest_cache`, `.ruff_cache`).
- Replace the "Hello" `main()` stub with a minimal entry point that does nothing Jira-related.

## Capabilities

### New Capabilities
- `project-foundation`: Package layout, supported Python version, dependency groups, and a working test and lint harness for the application.

### Modified Capabilities

## Impact

- Files: `pyproject.toml`, `.python-version`, `.gitignore`, `README.md`, `src/jira_dashboard/**`, `tests/**`, `docs/`.
- Dependencies: adds `pydantic-settings`, `keyring` (runtime); `pytest`, `ruff` (dev).
- Developer environment: must run through `uv` (default `python` on PATH is 3.9).
- No Jira access, no GUI, no behavior visible to end users.
