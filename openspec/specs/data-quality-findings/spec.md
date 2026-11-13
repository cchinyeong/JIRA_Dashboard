# data-quality-findings Specification

## Purpose
Defines the read-only detection of data-quality problems on Jira tickets, so the dashboard can highlight what needs correcting instead of hiding or guessing it.

## Requirements

### Requirement: Finding structure
Every finding SHALL have a code, a message that says what to correct, the field or relation concerned, and optionally the key of a related ticket.

#### Scenario: Finding content
- **WHEN** a finding is produced for a Task that has no parent
- **THEN** it has a code, a message naming the problem and no related ticket

### Requirement: Findings never fail a ticket
Findings SHALL be attached to the ticket they describe and MUST NOT make the ticket fail to map. They SHALL be derived only from the retrieved payload and MUST NOT cause any request or change to Jira. Their order MUST be deterministic.

#### Scenario: Ticket with findings still maps
- **WHEN** a ticket has a non-standard status and no parent
- **THEN** the ticket is returned with both findings

#### Scenario: Stable order
- **WHEN** the same payload is mapped twice
- **THEN** the findings are identical and in the same order

### Requirement: Non-standard status
A ticket whose status is not one of the official workflow statuses SHALL receive a finding that names the raw status Jira returned.

#### Scenario: Implemented status
- **WHEN** a ticket has the status "Implemented"
- **THEN** it has the unknown status, keeps the raw name "Implemented", and has a non-standard status finding naming it

#### Scenario: Official status
- **WHEN** a ticket has the status "In Progress"
- **THEN** it has no status finding

### Requirement: Task without a parent
A Task SHALL receive a finding when it has neither an Epic Link nor a link that qualifies as its parent. A Task with an Epic Link alone MUST NOT be flagged. Other ticket kinds MUST NOT receive this finding.

#### Scenario: Epic Link is enough
- **WHEN** a Task has an Epic Link and no "is child of" link
- **THEN** it has no parent finding

#### Scenario: Child of a risk
- **WHEN** a Task has no Epic Link and a link reading "is child of" to a Risk
- **THEN** it has no parent finding

#### Scenario: Only mentions
- **WHEN** a Task has no Epic Link and only "mentions" or "clones" links
- **THEN** it has a parent finding

#### Scenario: No links at all
- **WHEN** a Task has no Epic Link and no links
- **THEN** it has a parent finding

#### Scenario: Not a task
- **WHEN** a Risk has no links
- **THEN** it has no parent finding

### Requirement: Wrong Epic link
A Risk or Issue SHALL receive a finding when it is linked to an Epic by one of the configured wrong phrases (by default "is child of" and "created by"). The finding MUST name the Epic and the phrase and propose "is caused by". The Epic MUST NOT become the ticket's parent. A Risk or Issue with no Epic link, or linked by "is caused by", MUST NOT be flagged.

#### Scenario: Child of an epic
- **WHEN** a Risk has a link reading "is child of" to Epic CAE-1513
- **THEN** it has a wrong Epic link finding naming CAE-1513, and its parent key is absent

#### Scenario: Created by an epic
- **WHEN** an Issue has a link reading "created by" to an Epic
- **THEN** it has a wrong Epic link finding

#### Scenario: Correct link
- **WHEN** a Risk has a link reading "is caused by" to an Epic
- **THEN** it has no finding and the Epic is its parent

#### Scenario: No Epic link
- **WHEN** a Risk has no link to an Epic
- **THEN** it has no finding

### Requirement: Invalid values stay unknown
A date, timestamp or sprint that cannot be read SHALL become unknown and SHALL produce a finding naming the field, and the ticket MUST still be returned with its other data.

#### Scenario: Invalid target date
- **WHEN** a ticket has the target end value "31/13/2026"
- **THEN** its target end date is unknown, it has an invalid value finding naming the field, and its other fields are mapped

#### Scenario: Unreadable sprint
- **WHEN** the sprint value cannot be parsed
- **THEN** the ticket has no sprint and an invalid value finding

### Requirement: Absent optional data is not a finding
Missing estimates, requester, target dates, assignee or sprint SHALL remain unknown without a finding in this version.

#### Scenario: Ticket without estimate
- **WHEN** a ticket has no estimate, no requester and no assignee
- **THEN** it has no findings for them
