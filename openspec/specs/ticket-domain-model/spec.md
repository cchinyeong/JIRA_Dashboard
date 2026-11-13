# ticket-domain-model Specification

## Purpose
Defines the internal, Jira-independent models for tickets, sprints, projects, users, roles and domains that all application layers operate on instead of raw Jira payloads.

## Requirements

### Requirement: Ticket status values
The system SHALL represent a ticket's Jira status as one of exactly six values: NEW, REFINEMENT, BACKLOG, PLANNED, IN_PROGRESS, CLOSED.

#### Scenario: Known status
- **WHEN** a status is looked up by one of the six names
- **THEN** the matching status value is returned

#### Scenario: Unsupported status
- **WHEN** a status outside the six values, such as IMPLEMENTED, is requested
- **THEN** the lookup fails with an error

### Requirement: User roles
The system SHALL define the roles PROJECT_LEAD, DOMAIN_LEAD and DOMAIN_ENGINEER.

#### Scenario: Roles available
- **WHEN** the defined roles are listed
- **THEN** exactly these three roles are returned

### Requirement: Domain values
The system SHALL represent a ticket's domain as the Jira Simulation Type: STATIC, DYNAMIC, OPTICS, THERMAL, MOLDFLOW, CFD, ACOUSTIC, MULTIPHYSICS, OTHER, or UNSPECIFIED when none is set.

#### Scenario: None maps to unspecified
- **WHEN** a Simulation Type of "None" or an empty value is converted to a domain
- **THEN** the result is UNSPECIFIED

#### Scenario: Known type is case-insensitive
- **WHEN** the Simulation Type "Moldflow" is converted to a domain
- **THEN** the result is MOLDFLOW

#### Scenario: Unrecognised type
- **WHEN** a Simulation Type not in the list is converted to a domain
- **THEN** the result is OTHER and no error is raised

### Requirement: Ticket fields
A ticket SHALL carry its key, summary, description, project, issue type, domain, request drivers, assignee, reporter, requester, status, priority, target start and end dates, actual start and completion dates, created and updated timestamps, sprint, estimated and remaining effort, blocked reason and Jira URL. Optional values MUST be allowed to be absent.

#### Scenario: Minimal ticket
- **WHEN** a ticket is created with only its key, summary, project and status
- **THEN** it is created and all other optional fields are absent

#### Scenario: Request drivers
- **WHEN** a ticket has several Jira components
- **THEN** all of them are kept, in order, as its request drivers

### Requirement: Effort in days
The system SHALL express ticket effort in days as decimal numbers.

#### Scenario: Effort value
- **WHEN** a ticket has an estimated effort of 4 days
- **THEN** its estimated effort reads as 4.0

### Requirement: Derived blocked state
A ticket SHALL be reported as blocked if and only if its status is REFINEMENT. The blocked state MUST NOT be stored separately and MUST NOT depend on any board column name.

#### Scenario: Refinement is blocked
- **WHEN** a ticket has status REFINEMENT
- **THEN** it is reported as blocked

#### Scenario: Other statuses are not blocked
- **WHEN** a ticket has status BACKLOG or PLANNED
- **THEN** it is not reported as blocked

### Requirement: Requester is free text
A ticket's requester SHALL be an optional text value and MUST NOT be a user record.

#### Scenario: Requester absent
- **WHEN** a ticket is created without a requester
- **THEN** its requester is absent

### Requirement: Immutable models
All domain models SHALL be immutable after creation.

#### Scenario: Modification rejected
- **WHEN** a field of an existing ticket is assigned a new value
- **THEN** the assignment fails with an error and the ticket is unchanged

### Requirement: Sprint and project
A sprint SHALL carry its identifier, name, state and optional start and end dates. A project SHALL carry its key and name.

#### Scenario: Sprint with end date
- **WHEN** a sprint is created with an end date
- **THEN** the end date is available on the sprint
