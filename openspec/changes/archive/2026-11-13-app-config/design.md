# Design

## Context

`jira_dashboard.config` is an empty package, and `pydantic-settings` and `keyring` are already installed (archived `project-scaffold`). The domain models are done and keep the blocked rule hard-coded to `REFINEMENT`. Field IDs, working time and the requester template were confirmed during exploration. Python 3.15 provides `tomllib`.

## Goals / Non-Goals

**Goals:**
- One validated, immutable `Settings` object that the rest of the app receives; nothing reads files or environment directly.
- Confirmed VE values shipped as defaults; unknowns as explicit placeholders.

**Non-Goals:**
- Secrets, logging setup, Jira payload mapping (other MVP-0 changes).
- Making the blocked rule configurable: keeping one source of truth in the models.

## Decisions

- **`pydantic-settings` `BaseSettings` with nested `BaseModel` sections** (`jira`, `fields`, `working_time`, `requester`, `boards`, `risk`, `app`, `logging`), all `frozen=True` and `extra="forbid"`. Alternative: plain dataclasses plus manual TOML parsing; rejected because layered sources, validation and env overrides come for free.
- **Source order** (highest first): environment (`JIRA_DASHBOARD_` prefix, `__` nested delimiter), local file `settings.local.toml` (path overridable via `JIRA_DASHBOARD_CONFIG_FILE`), packaged `default.toml` inside `jira_dashboard/config/`. Implemented through `settings_customise_sources` with `TomlConfigSettingsSource`. The local file name matches the existing `*.local.toml` ignore rule.
- **Defaults ship in the package** (`default.toml`), so an installed app works without the repo. It carries no secrets by construction.
- **Credentials are impossible, not just discouraged:** there is no field for them and `extra="forbid"` turns any `token`/`password` key into a loading error.
- **Field mapping values are Jira field IDs as strings** (`customfield_12112`, or system fields such as `timeoriginalestimate`, `components`), validated against a simple pattern. `actual_start` is `None` (placeholder; changelog-derived later).
- **Placeholders:** `jira.base_url` defaults to `https://jira.invalid`; a helper `is_placeholder` property tells callers it is not configured. `.invalid` is a reserved TLD so it can never resolve by accident.
- **URL validation:** `https` scheme required, trailing slash stripped. Plain `http` is rejected for the on-prem server too, since the PAT travels in the header. TLS verification stays on; there is no setting to disable it.
- **Board maps:** `boards.project_lead` and `boards.active_sprint` are `dict[TicketStatus, str]` (keyed by the model enum), display only. `REFINEMENT` is absent from the sprint map.
- **Risk thresholds are provisional:** `amber_days_before_target = 3`, `stale_after_days = 5`. They exist so MVP-3 has a home for them; values are expected to change.
- **Logging section:** `level` (validated against standard names), `directory`. The logging change consumes it.
- **A `get_settings()` factory** builds settings once per call (no hidden global cache), so tests can pass explicit sources.

## Risks / Trade-offs

- [Strict `forbid` breaks on typos or stale override files] → Error messages name the key; this is preferred over silently ignoring a bad value.
- [Placeholder base URL could be mistaken for real] → `.invalid` host plus `is_placeholder`; `jira-client-interface` must refuse to connect while it is true.
- [`days_per_week` and risk thresholds are assumptions] → Documented as provisional in `docs/configuration.md`.
- [Env var nesting syntax is easy to get wrong] → Documented with an example.
