# Spec Delta

## MODIFIED Requirements

### Requirement: Ticket status values
The system SHALL represent a ticket's Jira status as one of the six workflow values NEW, REFINEMENT, BACKLOG, PLANNED, IN_PROGRESS, CLOSED, or UNKNOWN for any other status name.

#### Scenario: Known status
- **WHEN** a status is looked up by one of the six names
- **THEN** the matching status value is returned

#### Scenario: Unsupported status
- **WHEN** a status outside the six values, such as IMPLEMENTED, is looked up
- **THEN** the result is UNKNOWN and no error is raised

## ADDED Requirements

### Requirement: Raw status name
A ticket SHALL keep the status name exactly as Jira returned it, so that an unknown status can be shown and corrected.

#### Scenario: Unknown status keeps its name
- **WHEN** a ticket is created with status UNKNOWN and raw status "Implemented"
- **THEN** the raw status reads "Implemented"

### Requirement: Ticket findings
A ticket SHALL carry zero or more data-quality findings and MUST be immutable including its findings.

#### Scenario: Default
- **WHEN** a ticket is created without findings
- **THEN** its findings are empty

#### Scenario: Findings cannot be replaced
- **WHEN** code assigns new findings to an existing ticket
- **THEN** the assignment fails with an error
