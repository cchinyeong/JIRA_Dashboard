# Spec Delta

## Purpose

Defines the application layer between the Jira client and the user interface: refreshing data, keeping a consistent in-memory snapshot, and filtering, grouping and summarising tickets, with no dependency on the interface toolkit.

## ADDED Requirements

### Requirement: Refresh retrieves tickets and their parents
A refresh SHALL retrieve the team's tickets, then retrieve each referenced parent ticket that was not itself retrieved, repeating until no parent is missing or three rounds have run. Parents retrieved only to complete the hierarchy MUST be available by key but MUST NOT appear in the ticket list.

#### Scenario: Parents outside the search
- **WHEN** a retrieved Task refers to Epic CAE-1513 that the search did not return
- **THEN** the Epic is retrieved, can be looked up by key, and is not in the ticket list

#### Scenario: Parent of a parent
- **WHEN** a Task refers to a Risk that refers to an Epic, and neither was retrieved
- **THEN** both are retrieved over successive rounds

#### Scenario: Missing parent
- **WHEN** a referenced parent does not exist or cannot be seen
- **THEN** the refresh still succeeds and the Task's parent lookup returns nothing

### Requirement: Failed refresh keeps earlier data
If retrieving the team's tickets fails (authentication, network, timeout, missing token or any unexpected error), the refresh SHALL keep the previous data, report the failure with its kind and a user-readable message, and MUST NOT raise to the caller.

#### Scenario: Authentication failure with data present
- **WHEN** a refresh fails because Jira rejects the token after an earlier successful refresh
- **THEN** the earlier tickets remain available and the result reports an authentication failure

#### Scenario: First refresh fails
- **WHEN** the first refresh fails
- **THEN** the data is empty and the result reports the failure

#### Scenario: No token stored
- **WHEN** a refresh is attempted and no token is stored
- **THEN** the result reports a missing token with the instruction on how to store it

### Requirement: Parent retrieval failure is a warning
If only the retrieval of parents fails, the refresh SHALL still succeed with the tickets retrieved and SHALL report a warning that the hierarchy is incomplete.

#### Scenario: Parents unavailable
- **WHEN** the search succeeds and the parent retrieval times out
- **THEN** the tickets are available, the refresh succeeds, and a warning says parents could not be loaded

### Requirement: One refresh at a time
A refresh requested while another is running SHALL NOT start a second retrieval and SHALL report that a refresh is already running.

#### Scenario: Overlapping refresh
- **WHEN** a second refresh is requested while the first is in progress
- **THEN** the second returns immediately as already running and the client is queried only once

### Requirement: Consistent snapshot
Readers SHALL always see data from one complete refresh together with the time it finished, the tickets that could not be read and any warnings. Data MUST be replaced only when a refresh finishes successfully.

#### Scenario: Reading during a refresh
- **WHEN** tickets are read while a refresh is in progress
- **THEN** the previous refresh's data is returned unchanged

#### Scenario: Refresh time
- **WHEN** a refresh succeeds
- **THEN** the snapshot carries the completion time

### Requirement: Filtering
The service SHALL filter tickets by project, domain, assignee, sprint, status, priority, kind, free text and "has findings". Several values of one criterion are alternatives; different criteria all apply. An empty criterion applies no restriction. Unknown values MUST be selectable.

#### Scenario: Combined criteria
- **WHEN** the filter is domain Static or Dynamic, status In Progress
- **THEN** only In Progress tickets in those two domains are returned

#### Scenario: Unknown assignee
- **WHEN** the filter selects unknown for the assignee
- **THEN** only tickets without an assignee are returned

#### Scenario: Text search
- **WHEN** the text is "1558" or part of a summary
- **THEN** tickets whose key, summary, assignee or requester contain it, ignoring case, are returned

#### Scenario: Findings only
- **WHEN** the filter asks for tickets with findings
- **THEN** only tickets that have at least one finding are returned

### Requirement: Facets for filter controls
For each filterable field the service SHALL list the distinct values present with their ticket counts, including an unknown entry when some tickets lack a value.

#### Scenario: Assignee facet
- **WHEN** three tickets belong to one engineer, one to another, and two have no assignee
- **THEN** the facet lists the two engineers with 3 and 1 and an unknown entry with 2

### Requirement: Natural ticket order
Tickets SHALL be ordered by project key and then numerically by ticket number.

#### Scenario: Numeric order
- **WHEN** tickets CAE-100, CAE-99 and CAE-1000 are ordered
- **THEN** the order is CAE-99, CAE-100, CAE-1000

### Requirement: Hierarchy lookup and grouped view
The service SHALL return the parent and the children of a ticket, and a grouped view of a ticket list in which each ticket sits under its parent even when the parent is not in the list. Tasks without a parent MUST be listed separately.

#### Scenario: Task under risk under epic
- **WHEN** a Task refers to a Risk that refers to an Epic
- **THEN** the grouped view shows the Task under the Risk under the Epic

#### Scenario: Parent filtered out
- **WHEN** a filter excludes a Task's parent but includes the Task
- **THEN** the Task is shown under its parent, which is marked as not matching the filter

#### Scenario: Orphan tasks
- **WHEN** a Task has no parent key
- **THEN** it appears in the orphan list

### Requirement: Snapshot summary
The service SHALL summarise the data: ticket counts by kind and by status, the number of tickets with findings, finding counts by code, the number of unreadable tickets, and the time of the last successful refresh.

#### Scenario: Summary counts
- **WHEN** the data holds 3 Tasks and 2 Risks, one Task with a parent finding
- **THEN** the summary shows 3 Tasks, 2 Risks, 1 ticket with findings and 1 parent finding

### Requirement: Safe ticket link
The service SHALL provide a ticket's Jira link only when it begins with the configured Jira base URL, and nothing otherwise.

#### Scenario: Foreign link refused
- **WHEN** a ticket's link points to another host
- **THEN** no link is provided

### Requirement: Independent and read-only
The service MUST NOT depend on the user interface and MUST NOT write to Jira.

#### Scenario: Used without an interface
- **WHEN** the service is created with a Jira client and no interface code is imported
- **THEN** it refreshes, filters and summarises normally
