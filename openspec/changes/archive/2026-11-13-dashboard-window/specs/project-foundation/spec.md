# Spec Delta

## MODIFIED Requirements

### Requirement: Source layout
The application code SHALL live in a single `jira_dashboard` package under `src/`, with sub-packages for models, services, integrations, configuration, utilities and the user interface. Sub-packages for future capabilities MUST NOT be created before they have content.

#### Scenario: Package is importable
- **WHEN** `jira_dashboard` is imported in the project environment
- **THEN** the import succeeds and each sub-package is importable

#### Scenario: No premature folders
- **WHEN** the `src/jira_dashboard` tree is listed
- **THEN** it contains no `skills`, `agents`, `workflows` or `database` directories
