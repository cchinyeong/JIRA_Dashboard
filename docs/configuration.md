# Configuration

Settings are loaded by `jira_dashboard.config.get_settings()` into an immutable, validated object. Unknown keys and invalid values fail loading and name the key.

## Layers (highest priority first)

1. Environment variables, prefix `JIRA_DASHBOARD_`, nested with `__`.
2. Local file `settings.local.toml` in the working directory (git-ignored), or the path in `JIRA_DASHBOARD_CONFIG_FILE`.
3. Packaged defaults: `src/jira_dashboard/config/default.toml`.

Example `settings.local.toml`:

```toml
[jira]
base_url = "https://jira.example.com"
```

Equivalent environment variable:

```powershell
$env:JIRA_DASHBOARD_JIRA__BASE_URL = "https://jira.example.com"
```

## Secrets

Settings have no field for passwords, tokens or keys; a `token` or `password` key is rejected as unknown. Credentials are handled separately (see the secrets capability).

## Placeholders and provisional values

- `jira.base_url` defaults to `https://jira.invalid`; `settings.jira.is_placeholder` is true until it is overridden. The URL must be HTTPS.
- `fields.actual_start` is unset; the source will come from the changelog in a later MVP.
- `working_time.days_per_week = 5` and the `risk` thresholds are assumptions to be confirmed.
- `hours_per_day = 8` is confirmed for the VE Jira instance.

## Issue hierarchy

`issues.request_types` (Epic, Risk, Issue) and `issues.task_types` (Task) classify tickets; a type may not be in both lists. `fields.epic_link` is `customfield_10001`. `issues.parent_link_phrases` lists the issue link texts, exactly as Jira shows them on a Task (case-insensitive), that mean "this Task belongs to that Risk or Issue": by default `is child of` and `is caused by`. Add other phrases your team uses here; a Task linked by an unlisted phrase has no parent.

## Board maps

`boards.project_lead` and `boards.active_sprint` map a status to its column label. They are display-only; the blocked rule lives in the models (`REFINEMENT`).
