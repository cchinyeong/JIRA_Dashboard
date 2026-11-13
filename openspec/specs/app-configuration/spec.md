# app-configuration Specification

## Purpose
Defines how the application's non-secret settings are externalised, loaded, validated and overridden, so that Jira details, field IDs and thresholds never live in code.

## Requirements

### Requirement: Packaged defaults
The system SHALL ship default settings that load without any user-supplied file and describe the VE Jira project, including the confirmed custom-field IDs.

#### Scenario: Load defaults
- **WHEN** settings are loaded with no override file and no environment overrides
- **THEN** loading succeeds and the project key is `CAE` and the team filter is `Structural Analysis`

#### Scenario: Confirmed field IDs
- **WHEN** the field mapping is read from the defaults
- **THEN** it maps target start to `customfield_12112`, target end to `customfield_12113`, sprint to `customfield_10000`, team to `customfield_12110` and simulation type to `customfield_15253`

### Requirement: Layered overrides
The system SHALL apply overrides in increasing priority: packaged defaults, a local override file, then environment variables.

#### Scenario: Local file overrides default
- **WHEN** a local override file sets the Jira base URL
- **THEN** the loaded settings use that URL

#### Scenario: Environment overrides file
- **WHEN** both a local file and an environment variable set the same value
- **THEN** the environment value is used

### Requirement: Strict validation
The system MUST reject settings containing unknown keys or invalid values, and the error MUST identify the offending key.

#### Scenario: Unknown key
- **WHEN** an override contains a key that is not a defined setting
- **THEN** loading fails and the error names the key

#### Scenario: Non-HTTPS Jira URL
- **WHEN** the Jira base URL does not use HTTPS
- **THEN** loading fails

### Requirement: No secrets in settings
Settings SHALL NOT define any field for passwords, tokens, secrets or private keys, and such values MUST NOT be read from settings files.

#### Scenario: Credential key rejected
- **WHEN** an override file contains a key such as `token` or `password`
- **THEN** loading fails as an unknown key

### Requirement: Placeholders for unconfirmed values
Values that are not yet confirmed SHALL be present as explicit placeholders so the application can load, and a placeholder MUST be identifiable as such.

#### Scenario: Placeholder Jira URL
- **WHEN** defaults are loaded
- **THEN** the Jira base URL is a clearly marked placeholder and the actual-start field source is unset

### Requirement: Working-time conversion settings
The system SHALL provide hours per day (default 8) and days per week (default 5) for converting Jira time values to days. Both MUST be positive.

#### Scenario: Defaults
- **WHEN** defaults are loaded
- **THEN** hours per day is 8 and days per week is 5

#### Scenario: Invalid value
- **WHEN** hours per day is set to 0
- **THEN** loading fails

### Requirement: Requester template
The system SHALL provide the description panel title that holds the requester (`PIC (Requester - Full Name)`) and the placeholder texts that mean no requester is given (`Requester`).

#### Scenario: Template defaults
- **WHEN** defaults are loaded
- **THEN** the requester panel title is `PIC (Requester - Full Name)` and `Requester` is a listed placeholder

### Requirement: Board display maps
The system SHALL provide, for the Project Lead board and the Active Sprint board separately, a mapping from each ticket status to the board column label. These maps MUST be display-only.

#### Scenario: Different labels per board
- **WHEN** the maps are read for status BACKLOG
- **THEN** the Project Lead board maps it to Backlog and the Active Sprint board maps it to On Hold

#### Scenario: Refinement on the Project Lead board
- **WHEN** the Project Lead board map is read for REFINEMENT
- **THEN** it maps to On Hold

### Requirement: Risk, application and logging settings
The system SHALL externalise provisional risk thresholds, general application settings and logging settings (level and log directory), each with a valid default.

#### Scenario: Logging level validated
- **WHEN** the logging level is set to a value that is not a standard level name
- **THEN** loading fails

### Requirement: Settings are read-only
Loaded settings SHALL be immutable for the lifetime of the application.

#### Scenario: Modification rejected
- **WHEN** code assigns a new value to a loaded setting
- **THEN** the assignment fails with an error

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

### Requirement: Team identification
The system SHALL externalise the team's name (default `Structural Analysis`) and its numeric Jira team ID (default 400), which is what the team field is matched by. The ID MUST be a positive integer.

#### Scenario: Team defaults
- **WHEN** defaults are loaded
- **THEN** the team name is `Structural Analysis` and the team ID is 400

#### Scenario: Invalid team ID
- **WHEN** the team ID is set to 0 or a negative number
- **THEN** loading fails

### Requirement: Retrieval settings
The system SHALL externalise the search page size (default 100, between 1 and 1000), the maximum number of retries for transient failures (default 2, not negative) and the closed-ticket look-back in days (default 30, not negative).

#### Scenario: Retrieval defaults
- **WHEN** defaults are loaded
- **THEN** the page size is 100, the maximum retries is 2 and the look-back is 30 days

#### Scenario: Page size out of range
- **WHEN** the page size is set to 0 or 5000
- **THEN** loading fails

#### Scenario: Negative values rejected
- **WHEN** the maximum retries or the look-back is negative
- **THEN** loading fails

### Requirement: Data quality settings
The system SHALL externalise the issue types excluded from the dashboard (default Sub-task) and the link phrases that mark a wrong Epic link on a Risk or Issue (defaults "is child of" and "created by"), matched case-insensitively against the direction text Jira shows.

#### Scenario: Data quality defaults
- **WHEN** defaults are loaded
- **THEN** the excluded type is Sub-task and the wrong Epic link phrases are `is child of` and `created by`

#### Scenario: Correct phrase is not a wrong phrase
- **WHEN** defaults are loaded
- **THEN** `is caused by` is not among the wrong Epic link phrases
