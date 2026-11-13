# Spec Delta

## Purpose

Defines the filter bar that narrows the tickets shown in the main window by text and by type, status, domain, assignee, sprint and priority, or to tickets with data-quality findings.

## ADDED Requirements

### Requirement: Filter controls
The window SHALL show a filter bar with a text search, multi-select filters for Type, Status, Domain, Assignee, Sprint and Priority, an "Only with findings" switch and a Clear button. A ticket MUST match when it satisfies every active control; within one multi-select filter, matching any selected value is enough.

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

### Requirement: Filter values with counts
Each multi-select filter SHALL list the values present in the latest refresh with the number of tickets for each, counted over all tickets rather than the filtered ones, and SHALL list "Unknown" last. A non-standard status MUST appear as "Unknown" followed by its Jira name.

#### Scenario: Counts shown
- **WHEN** the user opens the Status filter
- **THEN** each status is listed with its ticket count, and a status with no tickets is not listed

#### Scenario: Unknown last
- **WHEN** some tickets have no assignee
- **THEN** "Unknown" is the last entry of the Assignee filter

### Requirement: Filters survive refresh
Active filters SHALL stay applied after a refresh. Selected values that no longer exist in the data MUST be dropped without an error.

#### Scenario: Filter kept
- **WHEN** a refresh finishes while a status filter is active
- **THEN** the same filter still applies to the new data

#### Scenario: Value disappears
- **WHEN** a refresh finishes and a selected sprint no longer exists
- **THEN** that value is removed from the filter and the remaining controls still apply

### Requirement: Empty result
When no ticket matches, the window SHALL say that no ticket matches the filters and offer to clear them, instead of showing an unexplained empty table.

#### Scenario: Nothing matches
- **WHEN** the active filters match no ticket
- **THEN** a message says so and the Clear button is available
