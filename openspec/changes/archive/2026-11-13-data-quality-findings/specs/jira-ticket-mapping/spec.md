# Spec Delta

## MODIFIED Requirements

### Requirement: Status mapping
The mapper SHALL convert the Jira status name to a ticket status and keep the raw name. A status that is not one of the six workflow statuses MUST map to the unknown status and MUST NOT fail the ticket.

#### Scenario: Unsupported status
- **WHEN** a payload has status IMPLEMENTED
- **THEN** the ticket maps with status UNKNOWN and raw status "Implemented"

## ADDED Requirements

### Requirement: Unusable payload
A payload without a ticket key, fields, project or summary SHALL be reported as a mapping error that names the ticket when its key is known. All other missing or invalid data MUST be mapped as unknown.

#### Scenario: Missing project
- **WHEN** a payload has no project
- **THEN** a mapping error naming the ticket key is raised

#### Scenario: Missing optional field
- **WHEN** a payload has no priority, assignee, sprint or estimates
- **THEN** the ticket maps with those values unknown
