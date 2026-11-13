# Proposal

## Why

MVP-0 requires Jira URL, field mappings, risk thresholds, application settings and logging settings to be externalised, with no Jira custom-field ID hard-coded in code. Exploration with the VE team has now confirmed the real on-prem field IDs, board layouts, working-time settings and requester template, so the configuration can be defined concretely instead of with placeholders.

## What Changes

- Add a typed, validated settings object loaded from TOML (shipped defaults, optional local overrides, environment overrides) using `pydantic-settings`.
- Ship defaults containing the confirmed VE values: Jira project `VE_CAE`, team filter `Structural Analysis`, and the field mapping (Team `customfield_12110`, Simulation Type `customfield_15253`, Target start `customfield_12112`, Target end `customfield_12113`, Sprint `customfield_10000`, Original/Remaining estimate `timeoriginalestimate`/`timeestimate`, Components).
- Keep unconfirmed values as explicit placeholders: the Jira base URL and the actual-start source.
- Add working-time settings (8 hours/day confirmed; 5 days/week assumed) and the requester-panel template (title and placeholder values).
- Add per-board status-to-column display maps for the Project Lead and Active Sprint boards.
- Add provisional risk thresholds, application settings and a logging section (consumed by `logging-secrets`).
- Reject unknown keys, non-HTTPS Jira URLs and any credential-like setting. Secrets are never part of settings.

## Capabilities

### New Capabilities
- `app-configuration`: Externalised, validated application settings including Jira connection details, field mapping, working time, board display maps, requester template, risk thresholds and logging settings.

### Modified Capabilities

## Impact

- Code: `src/jira_dashboard/config/**`, a packaged default TOML file, tests in `tests/unit/`.
- Dependencies: none new (`pydantic-settings` already added by `project-scaffold`; `tomllib` is in the standard library).
- Documentation: `docs/configuration.md`.
- Out of scope: reading secrets (`logging-secrets`), applying the field mapping to Jira payloads (`jira-client-interface`), making the blocked rule configurable (it stays derived from `REFINEMENT` in the models).
