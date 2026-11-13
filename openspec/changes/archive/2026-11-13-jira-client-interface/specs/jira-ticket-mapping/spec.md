# Spec Delta

## Purpose

Defines how Jira Server issue payloads are converted into internal ticket models, absorbing on-premises payload quirks in one place.

## ADDED Requirements

### Requirement: Field mapping from configuration
The mapper SHALL read custom and system fields using the configured field IDs and MUST NOT rely on hard-coded field IDs.

#### Scenario: Reconfigured field ID
- **WHEN** the configured target-end field ID is changed and the payload uses the new ID
- **THEN** the mapped ticket carries the target end date from the new field

### Requirement: Core ticket fields
The mapper SHALL map key, summary, description, project, issue type, priority, status, assignee, reporter, created and updated timestamps, and the browse URL of the issue.

#### Scenario: Sample ticket
- **WHEN** a payload for CAE-1558 in status In Progress, type Risk, priority Major is mapped
- **THEN** the ticket has that key, status IN_PROGRESS, issue type Risk, priority Major and a URL ending in `/browse/CAE-1558`

#### Scenario: Unassigned ticket
- **WHEN** the payload has no assignee
- **THEN** the ticket's assignee is absent

### Requirement: Status mapping
The mapper SHALL convert the Jira status name to a supported ticket status and MUST raise a mapping error naming the ticket when the status is not supported.

#### Scenario: Unsupported status
- **WHEN** a payload has status IMPLEMENTED
- **THEN** a mapping error naming the ticket key is raised

### Requirement: Dates
The mapper SHALL read target start and end as calendar dates from their configured fields, tolerate absent dates, and parse Jira timestamps with offsets.

#### Scenario: Target dates
- **WHEN** a payload has target start 2026-10-30 and target end 2026-11-11
- **THEN** the ticket carries those dates

#### Scenario: Timestamp offset
- **WHEN** the created timestamp is `2026-10-28T10:46:00.000+0800`
- **THEN** the ticket's created time is 10:46 at offset +08:00

### Requirement: Effort in days
The mapper SHALL convert estimate and remaining estimate from seconds to days using the configured hours per day, and SHALL leave them absent when Jira has no value.

#### Scenario: Four days
- **WHEN** the estimate is 115200 seconds and hours per day is 8
- **THEN** the ticket's estimated effort is 4.0 days

#### Scenario: No estimate
- **WHEN** the payload has no estimate
- **THEN** the estimated effort is absent

### Requirement: Domain and request drivers
The mapper SHALL map the Simulation Type field to a domain and the Components to the ordered request drivers.

#### Scenario: Static simulation with risk component
- **WHEN** the Simulation Type is Static and the only component is Risk
- **THEN** the domain is STATIC and the request drivers are Risk

#### Scenario: Missing simulation type
- **WHEN** the Simulation Type is absent
- **THEN** the domain is UNSPECIFIED

### Requirement: Sprint parsing
The mapper SHALL read the sprint from both the Jira Server legacy text format and the structured format, choose the active sprint when several are present, and otherwise the most recent one.

#### Scenario: Legacy format
- **WHEN** the sprint value is a legacy string with id 12, name `Static Sprint (Wk45- 46 26)`, state ACTIVE and an end date of 16 November 2026
- **THEN** the ticket's sprint has that id, name, state and end date

#### Scenario: Several sprints
- **WHEN** a ticket belongs to a closed sprint and an active sprint
- **THEN** the active sprint is chosen

#### Scenario: No sprint
- **WHEN** the sprint field is empty
- **THEN** the ticket's sprint is absent

### Requirement: Requester extraction
The mapper SHALL take the requester from the description panel whose title matches the configured requester title, trimmed of surrounding whitespace and trailing punctuation. A missing panel, an empty panel, or a panel containing a configured placeholder text MUST give no requester. Each ticket is read on its own: a task MUST NOT inherit a requester from another ticket in the mapper.

#### Scenario: Filled panel
- **WHEN** the description contains the panel `PIC (Requester - Full Name)` with the text `Mohamad Faizal.`
- **THEN** the requester is `Mohamad Faizal`

#### Scenario: Template left unfilled
- **WHEN** the panel text is the placeholder `Requester`
- **THEN** the requester is absent

#### Scenario: No panel
- **WHEN** the description has no requester panel
- **THEN** the requester is absent

### Requirement: Ticket kind mapping
The mapper SHALL classify a ticket as REQUEST when its issue type is one of the configured request types, TASK when it is one of the configured task types, and OTHER otherwise.

#### Scenario: Risk is a request
- **WHEN** a payload has issue type Risk
- **THEN** the ticket kind is REQUEST

#### Scenario: Task is a task
- **WHEN** a payload has issue type Task
- **THEN** the ticket kind is TASK

#### Scenario: Unlisted type
- **WHEN** a payload has an issue type that is in neither list
- **THEN** the ticket kind is OTHER

### Requirement: Parent mapping
The mapper SHALL set a task's parent key from the configured Epic Link field when it has a value; otherwise from an issue link whose direction text for this ticket matches a configured link phrase and whose other end is a Risk or Issue ticket. When several links qualify, the lowest key MUST be chosen so the result is deterministic. Tickets that are not tasks, and tasks with no qualifying reference, have no parent key.

#### Scenario: Epic Link
- **WHEN** a task payload has an Epic Link value CAE-1513
- **THEN** the task's parent key is CAE-1513

#### Scenario: Issue link to a risk
- **WHEN** a task payload has no Epic Link and an issue link reading "is child of" to Risk ticket CAE-1558
- **THEN** the task's parent key is CAE-1558

#### Scenario: Unrelated link ignored
- **WHEN** a task payload has no Epic Link and only an unrelated link phrase such as "blocks" to a Risk ticket, or a link to another Task
- **THEN** the task has no parent key

#### Scenario: Several qualifying links
- **WHEN** a task is linked to CAE-1592 and CAE-1558 as Issue and Risk
- **THEN** the parent key is CAE-1558

#### Scenario: Request has no parent
- **WHEN** an Epic payload is mapped
- **THEN** its parent key is absent

### Requirement: Mapping is pure
The mapper MUST NOT perform network access or read credentials, and MUST NOT modify its input payload.

#### Scenario: Input unchanged
- **WHEN** a payload is mapped
- **THEN** the payload is identical afterwards
