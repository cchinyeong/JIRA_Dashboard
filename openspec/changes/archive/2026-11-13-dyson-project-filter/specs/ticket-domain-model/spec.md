# Spec Delta

## ADDED Requirements

### Requirement: Dyson projects
A ticket SHALL carry the list of Dyson projects it belongs to, which MAY be empty and MAY hold several entries. An empty list means the project is unknown, not that the ticket belongs to no project.

#### Scenario: Ticket in two projects
- **WHEN** a ticket is created with the Dyson projects `898B` and `915`
- **THEN** the ticket exposes both, in that order

#### Scenario: Default
- **WHEN** a ticket is created without Dyson projects
- **THEN** its list of Dyson projects is empty
