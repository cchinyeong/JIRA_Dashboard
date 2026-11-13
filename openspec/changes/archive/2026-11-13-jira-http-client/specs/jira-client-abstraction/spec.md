# Spec Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Skeleton makes no network calls
**Reason**: The on-premises client now retrieves tickets from Jira; read-only behaviour is guaranteed by the HTTP access requirements instead.
**Migration**: Use `jira-http-access` for read-only, authentication and transport rules; the configuration guard still stops a client from being created before the Jira URL is set.

## ADDED Requirements

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
- **WHEN** a search returns three issues and one has an unsupported status
- **THEN** the batch contains two tickets and one failure naming the key and reason

#### Scenario: Request failure still raises
- **WHEN** a request itself fails with an authentication error
- **THEN** the error is raised and no partial batch is returned
