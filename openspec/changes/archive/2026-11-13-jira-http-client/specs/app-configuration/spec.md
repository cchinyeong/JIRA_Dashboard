# Spec Delta

## ADDED Requirements

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
