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

The **Jira setup** dialog (see [dashboard.md](dashboard.md)) writes `jira.base_url` into this local file for you. It changes only that line, keeps comments and every other setting, and refuses to touch a file it cannot update safely (invalid TOML, `jira` as an inline table, `base_url` twice). The address must use `https`, have a host, and contain no user name, password, path or query. Because environment variables rank higher, the dialog does not save while `JIRA_DASHBOARD_JIRA__BASE_URL` is set. The file is in the working directory, so start the application from the same folder each time (or set `JIRA_DASHBOARD_CONFIG_FILE`).

## Secrets

Settings have no field for passwords, tokens or keys; a `token` or `password` key is rejected as unknown. Credentials are handled separately (see the secrets capability).

## Placeholders and provisional values

- `jira.base_url` defaults to `https://jira.invalid`; `settings.jira.is_placeholder` is true until it is overridden. The URL must be HTTPS.
- `fields.actual_start` is unset; the source will come from the changelog in a later MVP.
- `working_time.days_per_week = 5` and the `risk` thresholds are assumptions to be confirmed.
- `hours_per_day = 8` is confirmed for the VE Jira instance.

## Retrieval

`jira.team_id` (default 400) is the Jira team the query selects. The Team field is a team picker, so Jira matches it by numeric ID and a query by name returns nothing; `jira.team` is kept as the readable name. `jira.page_size` (default 100, 1 to 1000) is how many issues each search request asks for. `jira.max_retries` (default 2, not negative) is how many times a transient failure (timeout, connection error, HTTP 429, 502, 503, 504) is retried. `jira.closed_lookback_days` (default 30, not negative) limits closed tickets to those updated within that many days; open tickets are always included.

```toml
[jira]
closed_lookback_days = 60
```

## Issue hierarchy

`issues.request_types` (Epic, Risk, Issue) and `issues.task_types` (Task) classify tickets; a type may not be in both lists. `issues.epic_type` (Epic) names the Epic type. `fields.epic_link` is `customfield_10001`. `fields.dyson_project_list` is `customfield_12901` (the multi-select "Dyson Project List"); it is optional, and when it is unset no project is read.

Parent rules use the link text exactly as Jira shows it on the ticket (case-insensitive):

- `issues.task_parent_phrases` (default `is child of`): a Task belongs to the Risk or Issue it is linked to this way. A Task's Epic comes from the Epic Link field.
- `issues.request_parent_phrases` (default `is caused by`): a Risk or Issue belongs to the Epic it is linked to this way.

"mentions" links are never used, because any ticket ID typed in a free-text field creates one. Add other phrases your team uses to these lists, for example in `settings.local.toml`:

```toml
[issues]
task_parent_phrases = ["is child of", "is part of"]
```

Data quality settings: `issues.excluded_types` (default `Sub-task`) lists issue types the team search leaves out of the dashboard; set it to an empty list to include everything. `issues.request_wrong_epic_phrases` (default `is child of`, `created by`) are the link texts that flag a Risk or Issue as wrongly linked to an Epic (the correct text is `is caused by`). See [data-quality.md](data-quality.md).

The former single key `issues.parent_link_phrases` no longer exists; a file that still sets it fails to load. `jira.project_key` is the Jira project key (`CAE`); `VE_CAE` is only the project's name.

## Board maps

`boards.project_lead` and `boards.active_sprint` map a status to its column label. They are display-only; the blocked rule lives in the models (`REFINEMENT`).
