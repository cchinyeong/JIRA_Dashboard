# Spec Delta

## MODIFIED Requirements

### Requirement: Team-scoped query
The client SHALL build the ticket query from settings so that it is limited to the configured project key and team, and SHALL optionally limit it to tickets in open or future sprints. Values MUST be quoted so that they cannot alter the query.

#### Scenario: Project and team scope
- **WHEN** the query is built with default settings
- **THEN** it restricts to project `CAE` and team `Structural Analysis` using the configured team field

#### Scenario: Active sprint scope
- **WHEN** the query is built for tickets in sprints only
- **THEN** it additionally restricts to tickets in open or future sprints

#### Scenario: Quote in team name
- **WHEN** the configured team name contains a double quote
- **THEN** the quote is escaped in the query
