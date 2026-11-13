# Spec Delta

## ADDED Requirements

### Requirement: Issue hierarchy settings
The system SHALL externalise which Jira issue types are requests (default Epic, Risk, Issue) and which are tasks (default Task), the field that holds the Epic Link (default `customfield_10001`), and the issue link phrases that associate a task with a Risk or Issue (default `is child of` and `is caused by`). Phrases MUST match the link direction text shown in Jira, case-insensitively.

#### Scenario: Default issue types
- **WHEN** defaults are loaded
- **THEN** the request types are Epic, Risk and Issue and the task type is Task

#### Scenario: Epic Link and link phrases
- **WHEN** defaults are loaded
- **THEN** the Epic Link field is `customfield_10001` and the link phrases are `is child of` and `is caused by`

#### Scenario: Overlapping types rejected
- **WHEN** an issue type is configured as both a request type and a task type
- **THEN** loading fails and the error names the type
