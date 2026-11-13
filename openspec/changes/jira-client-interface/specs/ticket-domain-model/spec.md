# Spec Delta

## ADDED Requirements

### Requirement: Ticket kind
The system SHALL classify every ticket as REQUEST, TASK or OTHER. Requests are the Epic, Risk and Issue tickets that carry a delivery driver; tasks are the work items executed in sprints.

#### Scenario: Kind values
- **WHEN** the defined ticket kinds are listed
- **THEN** exactly REQUEST, TASK and OTHER are returned

#### Scenario: Default kind
- **WHEN** a ticket is created without specifying a kind
- **THEN** its kind is OTHER

### Requirement: Parent reference
A ticket SHALL carry an optional key of the request ticket it belongs to, and a task MAY refer to exactly one request. The reference MUST be a key and MUST NOT embed the parent ticket.

#### Scenario: Task with parent
- **WHEN** a task ticket is created with parent key CAE-1513
- **THEN** its parent key reads CAE-1513

#### Scenario: Request without parent
- **WHEN** a request ticket is created without a parent key
- **THEN** its parent key is absent
