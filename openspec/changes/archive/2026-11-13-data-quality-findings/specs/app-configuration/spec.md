# Spec Delta

## ADDED Requirements

### Requirement: Data quality settings
The system SHALL externalise the issue types excluded from the dashboard (default Sub-task) and the link phrases that mark a wrong Epic link on a Risk or Issue (defaults "is child of" and "created by"), matched case-insensitively against the direction text Jira shows.

#### Scenario: Data quality defaults
- **WHEN** defaults are loaded
- **THEN** the excluded type is Sub-task and the wrong Epic link phrases are `is child of` and `created by`

#### Scenario: Correct phrase is not a wrong phrase
- **WHEN** defaults are loaded
- **THEN** `is caused by` is not among the wrong Epic link phrases
