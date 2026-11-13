# Spec Delta

## Purpose

Defines the baseline repository structure, supported runtime and developer tooling that every other capability of the VE Jira Operations Dashboard builds on.

## ADDED Requirements

### Requirement: Supported Python version
The project SHALL declare Python 3.15 or newer as its minimum supported version, consistently in its pinned interpreter version and its package metadata.

#### Scenario: Version declarations agree
- **WHEN** the pinned interpreter version and the package's minimum Python requirement are read
- **THEN** both specify Python 3.15 or newer

#### Scenario: Package installs on the supported interpreter
- **WHEN** the project and its dependencies are installed on Python 3.15.2
- **THEN** installation succeeds

### Requirement: Source layout
The application code SHALL live in a single `jira_dashboard` package under `src/`, with sub-packages for models, services, integrations, configuration and utilities. Sub-packages for future capabilities MUST NOT be created before they have content.

#### Scenario: Package is importable
- **WHEN** `jira_dashboard` is imported in the project environment
- **THEN** the import succeeds and each MVP-0 sub-package is importable

#### Scenario: No premature folders
- **WHEN** the `src/jira_dashboard` tree is listed
- **THEN** it contains no `skills`, `agents`, `workflows`, `ui` or `database` directories

### Requirement: Test harness
The project SHALL provide a test suite organised into unit and integration directories that runs with a single documented command.

#### Scenario: Tests run
- **WHEN** the documented test command is run on a fresh checkout
- **THEN** the suite executes and passes, discovering tests under `tests/`

### Requirement: Lint and format checks
The project SHALL provide a documented lint and format check command that passes on the committed code.

#### Scenario: Checks pass
- **WHEN** the documented lint and format check command is run
- **THEN** it exits successfully with no violations

### Requirement: Secrets excluded from version control
The repository SHALL ignore local environment files and local configuration overrides so that credentials are not committed.

#### Scenario: Local secret files are ignored
- **WHEN** a `.env` file or a `*.local.toml` file is created in the repository
- **THEN** version control reports it as ignored
