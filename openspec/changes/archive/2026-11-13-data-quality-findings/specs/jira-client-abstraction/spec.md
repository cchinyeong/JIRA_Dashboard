# Spec Delta

## MODIFIED Requirements

### Requirement: Per-ticket failure isolation
Search and retrieval by several keys SHALL return a batch containing the tickets that mapped and a failure record, with key and reason, for each issue that could not be mapped. One failing issue MUST NOT prevent the others from being returned.

#### Scenario: One unmappable ticket
- **WHEN** a search returns three issues and one has no project
- **THEN** the batch contains two tickets and one failure naming the key and reason

#### Scenario: Request failure still raises
- **WHEN** a request itself fails with an authentication error
- **THEN** the error is raised and no partial batch is returned

## ADDED Requirements

### Requirement: Excluded issue types
The team search SHALL exclude tickets of the configured excluded issue types (default Sub-task). Retrieval by explicit keys MUST NOT apply this exclusion.

#### Scenario: Sub-tasks excluded
- **WHEN** the team query is built with default settings
- **THEN** it excludes issue type Sub-task

#### Scenario: Nothing excluded
- **WHEN** the excluded types are configured as empty
- **THEN** the query has no issue type restriction

#### Scenario: Explicit keys
- **WHEN** a Sub-task is requested by its key
- **THEN** it is returned
