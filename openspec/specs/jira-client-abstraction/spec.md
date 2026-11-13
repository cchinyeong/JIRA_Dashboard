# jira-client-abstraction Specification

## Purpose
Defines the Jira-agnostic client contract and the on-premises client skeleton, so the rest of the application depends on internal models and the Jira deployment can be swapped without redesign.

## Requirements

### Requirement: Jira-agnostic client interface
The system SHALL define a client interface for reading tickets whose operations return only internal ticket models, or batches of them with per-ticket failure records, and expose no Jira payload types. It SHALL allow fetching one ticket, fetching several tickets by key (so the requests that sprint tasks belong to can be loaded), and searching the team's tickets.

#### Scenario: Interface cannot be used directly
- **WHEN** the abstract client is instantiated
- **THEN** instantiation fails

#### Scenario: Operations return internal models
- **WHEN** a client implementation fetches a ticket by key
- **THEN** the result is an internal ticket model

#### Scenario: Fetch by several keys
- **WHEN** a client implementation fetches the keys CAE-1513 and CAE-1558
- **THEN** it returns a batch holding internal ticket models for those keys

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
The client SHALL build the ticket query from settings so that it is limited to the configured project key and the configured team, matching the team by its numeric ID because the team field does not accept names, and SHALL optionally limit it to tickets in open or future sprints. Text values MUST be quoted so that they cannot alter the query.

#### Scenario: Project and team scope
- **WHEN** the query is built with default settings
- **THEN** it restricts to project `CAE` and team ID 400 using the configured team field

#### Scenario: Active sprint scope
- **WHEN** the query is built for tickets in sprints only
- **THEN** it additionally restricts to tickets in open or future sprints

#### Scenario: Quote in team name
- **WHEN** the configured team name contains a double quote
- **THEN** the query still matches by the numeric team ID and contains no part of the name

### Requirement: Ticket retrieval
The on-premises client SHALL retrieve a ticket by key, several tickets by key, and the team's tickets, converting every issue with the ticket mapper. It SHALL read the stored token only when the first request is made.

#### Scenario: One ticket
- **WHEN** a ticket is requested by key
- **THEN** the mapped ticket is returned

#### Scenario: Ticket not found
- **WHEN** a requested ticket does not exist
- **THEN** a not-found error naming the key is raised

#### Scenario: Token read on first use
- **WHEN** the client is created and no request has been made
- **THEN** the credential store has not been read

#### Scenario: Missing token
- **WHEN** a request is made and no token is stored
- **THEN** an error explains how to store the token

### Requirement: Retrieval by several keys
Fetching several tickets by key SHALL validate every key, request the tickets in chunks of bounded size, and return those found. Keys that Jira does not return MUST be omitted from the batch, not reported as failures.

#### Scenario: Chunked request
- **WHEN** 120 valid keys are requested and the chunk size is 50
- **THEN** three requests are made and the found tickets are returned together

#### Scenario: Invalid key rejected
- **WHEN** a key does not look like a ticket key
- **THEN** it is rejected before any request is made

#### Scenario: Missing key omitted
- **WHEN** one of the requested keys does not exist
- **THEN** the other tickets are returned and the missing one is absent

### Requirement: Closed ticket look-back
The team search SHALL return every open ticket and only those closed tickets updated within the configured look-back days. Results MUST be ordered by ticket key so that paging is stable.

#### Scenario: Default look-back
- **WHEN** the query is built with default settings
- **THEN** it keeps tickets whose status is not Closed or that were updated within the last 30 days, ordered by key

#### Scenario: Look-back configured
- **WHEN** the look-back is set to 7 days
- **THEN** the query uses 7 days

### Requirement: Per-ticket failure isolation
Search and retrieval by several keys SHALL return a batch containing the tickets that mapped and a failure record, with key and reason, for each issue that could not be mapped. One failing issue MUST NOT prevent the others from being returned.

#### Scenario: One unmappable ticket
- **WHEN** a search returns three issues and one has no project
- **THEN** the batch contains two tickets and one failure naming the key and reason

#### Scenario: Request failure still raises
- **WHEN** a request itself fails with an authentication error
- **THEN** the error is raised and no partial batch is returned

### Requirement: Excluded issue types
The team search SHALL exclude tickets of the configured excluded issue types (default Sub-task). Retrieval by explicit keys MUST NOT apply this exclusion.

#### Scenario: Sub-tasks excluded
- **WHEN** the team query is built with default settings
- **THEN** it excludes issue type Sub-task

#### Scenario: Nothing excluded
- **WHEN** the excluded types are configured as empty
- **THEN** the query has no issue type restriction

#### Scenario: Explicit keys
- **WHEN** a Sub-task is requested by its key
- **THEN** it is returned
