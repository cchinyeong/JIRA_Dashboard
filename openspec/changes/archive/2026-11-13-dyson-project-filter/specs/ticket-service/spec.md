# Spec Delta

## MODIFIED Requirements

### Requirement: Filtering
The service SHALL filter tickets by project, Dyson project, domain, assignee, sprint, status, priority, kind, free text and "has findings". Several values of one criterion are alternatives; different criteria all apply. An empty criterion applies no restriction. Unknown values MUST be selectable. A ticket with several Dyson projects matches when any of them is selected.

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

#### Scenario: Ticket with several Dyson projects
- **WHEN** the filter selects the Dyson project `915` and a ticket belongs to `898B` and `915`
- **THEN** that ticket is returned

#### Scenario: Unknown Dyson project
- **WHEN** the filter selects unknown for the Dyson project
- **THEN** only tickets without any Dyson project are returned

### Requirement: Facets for filter controls
For each filterable field the service SHALL list the distinct values present with their ticket counts, including an unknown entry when some tickets lack a value. A ticket with several Dyson projects MUST be counted once under each of them, and the Dyson project values SHALL be ordered naturally, numbers by numeric value before names.

#### Scenario: Assignee facet
- **WHEN** three tickets belong to one engineer, one to another, and two have no assignee
- **THEN** the facet lists the two engineers with 3 and 1 and an unknown entry with 2

#### Scenario: Dyson project facet
- **WHEN** one ticket belongs to `898B` and `915`, another to `915`, and a third to `1000`
- **THEN** the facet lists `915` with 2, `898B` with 1 and `1000` with 1, ordered `898B`, `915`, `1000`, with an unknown entry only if some ticket has no project
