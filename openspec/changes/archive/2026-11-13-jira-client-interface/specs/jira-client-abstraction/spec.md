# Spec Delta

## Purpose

Defines the Jira-agnostic client contract and the on-premises client skeleton, so the rest of the application depends on internal models and the Jira deployment can be swapped without redesign.

## ADDED Requirements

### Requirement: Jira-agnostic client interface
The system SHALL define a client interface for reading tickets whose operations return only internal ticket models and expose no Jira payload types. It SHALL allow fetching one ticket, fetching several tickets by key (so the requests that sprint tasks belong to can be loaded), and searching the team's tickets.

#### Scenario: Interface cannot be used directly
- **WHEN** the abstract client is instantiated
- **THEN** instantiation fails

#### Scenario: Operations return internal models
- **WHEN** a client implementation fetches a ticket by key
- **THEN** the result is an internal ticket model

#### Scenario: Fetch by several keys
- **WHEN** a client implementation fetches the keys CAE-1513 and CAE-1558
- **THEN** it returns internal ticket models for those keys

### Requirement: On-premises client implements the interface
The system SHALL provide an on-premises Jira client that implements the client interface.

#### Scenario: Substitutable
- **WHEN** an on-premises client is created with valid settings
- **THEN** it can be used wherever the client interface is expected

### Requirement: Configuration guard
The on-premises client MUST refuse to be created while the Jira base URL is still the placeholder, and the error SHALL tell the user which setting to configure.

#### Scenario: Placeholder URL
- **WHEN** a client is created with the default placeholder base URL
- **THEN** creation fails with an error naming the Jira base URL setting

### Requirement: Team-scoped query
The client SHALL build the ticket query from settings so that it is limited to the configured project and team, and SHALL optionally limit it to tickets in active sprints. Values MUST be quoted so that they cannot alter the query.

#### Scenario: Project and team scope
- **WHEN** the query is built with default settings
- **THEN** it restricts to project `VE_CAE` and team `Structural Analysis` using the configured team field

#### Scenario: Active sprint scope
- **WHEN** the query is built for active sprints only
- **THEN** it additionally restricts to tickets in open sprints

#### Scenario: Quote in team name
- **WHEN** the configured team name contains a double quote
- **THEN** the quote is escaped in the query

### Requirement: Skeleton makes no network calls
Until remote access is implemented, the client's read operations SHALL fail with a clear not-implemented error and MUST NOT contact Jira or read credentials.

#### Scenario: Fetch not available yet
- **WHEN** a ticket fetch is requested on the skeleton client
- **THEN** a not-implemented error is raised and no network connection is attempted
