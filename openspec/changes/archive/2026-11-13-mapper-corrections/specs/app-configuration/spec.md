# Spec Delta

## MODIFIED Requirements

### Requirement: Packaged defaults
The system SHALL ship default settings that load without any user-supplied file and describe the VE Jira project, including the confirmed custom-field IDs.

#### Scenario: Load defaults
- **WHEN** settings are loaded with no override file and no environment overrides
- **THEN** loading succeeds and the project key is `CAE` and the team filter is `Structural Analysis`

#### Scenario: Confirmed field IDs
- **WHEN** the field mapping is read from the defaults
- **THEN** it maps target start to `customfield_12112`, target end to `customfield_12113`, sprint to `customfield_10000`, team to `customfield_12110` and simulation type to `customfield_15253`

### Requirement: Issue hierarchy settings
The system SHALL externalise the request issue types (default Epic, Risk, Issue), the task types (default Task), the Epic type (default Epic), the Epic Link field (default `customfield_10001`), and the link phrases that identify a parent: for tasks default "is child of", for Risks and Issues default "is caused by". Phrases match the direction text shown in Jira, case-insensitively.

#### Scenario: Default issue types
- **WHEN** defaults are loaded
- **THEN** the request types are Epic, Risk and Issue, the task type is Task and the Epic type is Epic

#### Scenario: Epic Link and link phrases
- **WHEN** defaults are loaded
- **THEN** the Epic Link field is `customfield_10001`, the task parent phrase is `is child of` and the request parent phrase is `is caused by`

#### Scenario: Mentions is not a default
- **WHEN** defaults are loaded
- **THEN** no parent phrase is `mentions` or `is mentioned by`

#### Scenario: Overlapping types rejected
- **WHEN** an issue type is configured as both a request type and a task type
- **THEN** loading fails and the error names the type

#### Scenario: Old combined setting rejected
- **WHEN** an override still sets the former single link phrase list
- **THEN** loading fails and the error names that key
