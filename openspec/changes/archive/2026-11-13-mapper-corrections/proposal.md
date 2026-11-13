# Proposal

## Why

The live check against the real VE Jira (archived `jira-live-data-check`) showed that three assumptions in the mapper and configuration were wrong or unsafe. A Risk's links are mostly "mentions" (created by any ticket ID typed in free text), which says nothing about hierarchy; the ticket hierarchy has a level we had not modelled (Risk or Issue under an Epic); the real project key is `CAE` (`VE_CAE` is only the name); and Tasks sit in future sprints that the active-sprint query would miss. These must be fixed before the HTTP client and dashboard rely on them.

## What Changes

- Parent rules become per ticket kind:
  - Task: its Epic Link, otherwise the Risk or Issue it "is child of".
  - Risk or Issue: the Epic it "is caused by".
  - Epics have no parent.
  - "mentions" never defines a parent.
- Configuration splits the link phrases into task phrases (default `is child of`) and request phrases (default `is caused by`), adds the Epic type name (default `Epic`), and removes the single mixed phrase list.
- `jira.project_key` default becomes `CAE`.
- The query option that limits to sprints now covers open and future sprints, and is renamed to match.
- The sanitised live fixtures become regression tests for the real payload shapes (skipped when the fixtures are not present).
- Documentation follows.

## Capabilities

### New Capabilities

### Modified Capabilities
- `jira-ticket-mapping`: Parent mapping becomes per-kind and excludes "mentions".
- `app-configuration`: Packaged defaults use project key `CAE`; issue hierarchy settings gain separate task and request link phrases and the Epic type.
- `jira-client-abstraction`: The team-scoped query uses the project key and can include future sprints.

## Impact

- Code: `config/settings.py`, `config/default.toml`, `integrations/jira_mapping.py`, `integrations/jira_client.py`, `integrations/jira_onprem.py`, and their tests.
- Behaviour change: `issues.parent_link_phrases` is removed in favour of `issues.task_parent_phrases` and `issues.request_parent_phrases`; a local override still using the old key will fail loading with the key named.
- Docs: `docs/configuration.md`, `docs/jira-integration.md`.
- Out of scope: Jira Cloud cross-project parents (MVP-9), the HTTP client, data-quality reporting of tasks without a parent (service layer).
