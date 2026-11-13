# Spec Delta

## MODIFIED Requirements

### Requirement: Filter controls
The window SHALL show a filter bar with a text search, multi-select filters for Type, Status, Domain, Dyson Project, Assignee, Sprint and Priority, an "Only with findings" switch and a Clear button. A ticket MUST match when it satisfies every active control; within one multi-select filter, matching any selected value is enough.

#### Scenario: Several filters combined
- **WHEN** the user selects the status In Progress and the domain Dynamic
- **THEN** only tickets that are In Progress and Dynamic are shown

#### Scenario: Several values of one filter
- **WHEN** the user selects the assignees Ann and Bob
- **THEN** tickets assigned to either are shown

#### Scenario: Text search
- **WHEN** the user types text that occurs in a ticket's key, summary, requester or assignee name
- **THEN** only tickets containing that text, ignoring case, are shown

#### Scenario: Only with findings
- **WHEN** the user switches on "Only with findings"
- **THEN** only tickets with at least one finding are shown

#### Scenario: Clear
- **WHEN** the user presses Clear
- **THEN** every control returns to its neutral state and all tickets are shown

#### Scenario: Dyson project
- **WHEN** the user selects the Dyson Project `898B` together with the status In Progress
- **THEN** only In Progress tickets that belong to `898B`, possibly among other projects, are shown

#### Scenario: Dyson project menu
- **WHEN** the user opens the Dyson Project filter
- **THEN** each project is listed with its ticket count, ordered naturally, with "Unknown" last when some tickets have none
