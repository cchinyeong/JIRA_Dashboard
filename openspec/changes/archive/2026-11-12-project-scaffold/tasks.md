# Tasks

## 1. Python version and dependencies

- [x] 1.1 Set `.python-version` to 3.15 and `requires-python` to `>=3.15` in `pyproject.toml`; verify `uv run python --version` prints 3.15.x
- [x] 1.2 Add runtime dependencies `pydantic-settings` and `keyring` and a dev group with `pytest` and `ruff`; verify `uv sync` succeeds and writes `uv.lock`

## 2. Layout and ignore rules

- [x] 2.1 Create `src/jira_dashboard/{models,services,integrations,config,utils}/__init__.py`, and `tests/unit`, `tests/integration`, `docs/`; verify no `skills`, `agents`, `workflows`, `ui` or `database` folders exist
- [x] 2.2 Replace the "Hello" stub in `src/jira_dashboard/__init__.py` with a minimal `main()` that does no Jira work; verify `uv run jira-dashboard` exits cleanly
- [x] 2.3 Extend `.gitignore` with `.env`, `*.local.toml`, `.pytest_cache/` and `.ruff_cache/`; verify with `git check-ignore .env x.local.toml`

## 3. Test and lint harness

- [x] 3.1 Configure pytest (`testpaths`, `pythonpath`) and ruff in `pyproject.toml`
- [x] 3.2 Add `tests/unit/test_package.py` that imports `jira_dashboard` and each MVP-0 sub-package; verify `uv run pytest` passes
- [x] 3.3 Verify `uv run ruff check` and `uv run ruff format --check` pass
- [x] 3.4 Document install, test and lint commands (all via `uv`) in `README.md`; verify each documented command runs as written
