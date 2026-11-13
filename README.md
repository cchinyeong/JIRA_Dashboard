# VE Jira Operations Dashboard

Standalone Windows desktop application for the Virtual Engineering team (Jira on-premises first).

Requires Python 3.15+. Run everything through [uv](https://docs.astral.sh/uv/); the `python` on PATH may be older.

```powershell
uv sync                      # install dependencies
uv run pytest                # run tests
uv run ruff check            # lint
uv run ruff format --check   # format check
uv run jira-dashboard        # run the application
```

See [docs/dashboard.md](docs/dashboard.md) for the window, its columns and what to do when a refresh fails.

Never commit credentials. Local secrets and overrides belong in `.env` or `*.local.toml`, both git-ignored.
