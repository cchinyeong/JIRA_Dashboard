# Design

## Context

Greenfield `uv` project: `uv_build` backend, `src/` layout, a stub `main()`, and the interpreter pinned at 3.9 (see proposal.md). The default `python` on PATH is 3.9, but `uv` has CPython 3.15.2 available, and `pydantic-settings`, `keyring` and `pytest` were verified to install on it in a throwaway venv.

## Goals / Non-Goals

**Goals:**
- One reproducible command each for install, test and lint, all run via `uv`.
- A layout later MVPs can extend without moving files.

**Non-Goals:**
- Any model, config, secret or Jira code (handled by later changes).
- CI pipelines or packaging/installer work for the Windows desktop build.

## Decisions

- **`uv` as the only workflow tool** (`uv sync`, `uv run pytest`, `uv run ruff check`). Alternative: bare `pip`/venv. Rejected because the repo already uses `uv`, and the system Python is 3.9.
- **Python floor 3.15 via `.python-version` and `requires-python = ">=3.15"`.** Lets later code use modern typing and `tomllib` without compatibility shims.
- **Dependencies:** runtime `pydantic-settings`, `keyring`; dev group `pytest`, `ruff` in `[dependency-groups] dev`. Adding runtime libraries now, not in their own changes, so one lock file covers MVP-0.
- **`ruff` for lint and format** instead of black + flake8 + isort: one tool, one config block.
- **Layout inside the package** (`src/jira_dashboard/{models,services,integrations,config,utils}`) rather than top-level `/src/models`, as the existing package is `jira_dashboard`. Each sub-package gets an `__init__.py` only.
- **Tests mirror the package** under `tests/unit` and `tests/integration`, with a single smoke test proving the harness and imports work.
- **`.gitignore`** gains `.env`, `*.local.toml` and tool caches.

## Risks / Trade-offs

- [Python 3.15 is new and some wheels may lag] → Dependencies were verified installable; pin via `uv.lock` and re-check when adding packages.
- [Contributors running bare `python` get 3.9] → README states that all commands go through `uv run`.
- [Adding dependencies before use] → Both are required by the next two changes; small cost.
