# Spec Delta

## ADDED Requirements

### Requirement: Dyson projects in the details
The panel SHALL show the ticket's Dyson projects, separated by commas, in the planning information, and "Unknown" in the unknown style when the ticket has none.

#### Scenario: Several projects
- **WHEN** a ticket belonging to `898B` and `915` is selected
- **THEN** the panel shows "898B, 915" as its Dyson projects

#### Scenario: No project
- **WHEN** a ticket without Dyson projects is selected
- **THEN** the panel shows "Unknown" in the unknown style
