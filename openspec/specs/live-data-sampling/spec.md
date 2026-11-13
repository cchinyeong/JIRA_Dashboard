# live-data-sampling Specification

## Purpose
Defines a read-only check that retrieves a few real Jira tickets, verifies field assumptions, and produces sanitised fixtures and a compatibility report without exposing credentials or ticket content.

## Requirements

### Requirement: Read-only access
The check SHALL only issue HTTP GET requests and MUST NOT create, modify or transition anything in Jira.

#### Scenario: Only GET is used
- **WHEN** the check runs against a recorded transport
- **THEN** every request made uses the GET method

### Requirement: Credentials and transport security
The check SHALL read the Jira PAT from the credential store, send it only as an authorization header, and MUST NOT print it. TLS certificate verification MUST remain enabled and use the operating system's trusted certificates; there is no option to disable it.

#### Scenario: Token never printed
- **WHEN** the check runs and fails or succeeds
- **THEN** neither the console output nor any written file contains the token value

#### Scenario: Placeholder URL refused
- **WHEN** the Jira base URL is still the placeholder
- **THEN** the check stops before any request and names the setting to configure

#### Scenario: Missing token
- **WHEN** no PAT is stored
- **THEN** the check stops with a message explaining how to store it

### Requirement: Minimal retrieval
The check SHALL request only the configured fields it needs for the specified tickets, and SHALL retrieve the Jira field list once to verify the configured field IDs.

#### Scenario: Field ID mismatch reported
- **WHEN** a configured field ID is absent from Jira's field list or has an unexpected name
- **THEN** the report names the setting, the configured ID and what Jira returned

### Requirement: Allow-list sanitisation
Sanitised output SHALL contain only allow-listed structural data. People MUST be replaced by consistent synthetic users, summaries by generic text, and description panel contents by placeholders, except that panel titles and a placeholder requester name are kept so requester parsing can be tested. URLs, avatars and any field not on the allow-list MUST be removed.

#### Scenario: People replaced consistently
- **WHEN** the same person appears as assignee and reporter
- **THEN** both are replaced by the same synthetic user and no real name or email remains

#### Scenario: Free text removed
- **WHEN** a ticket has a summary and a description with several panels
- **THEN** the sanitised ticket has a generic summary and a description containing only the panel titles and placeholder contents

#### Scenario: Unknown field dropped
- **WHEN** the response contains a field that is not on the allow-list
- **THEN** it is absent from the sanitised output

### Requirement: Structure preserved for mapper testing
Sanitisation MUST preserve the structure the mapper depends on: ticket keys, issue types, statuses, priorities, components, simulation type, dates, estimates, sprint values, Epic Link values, and issue link texts with linked keys and issue types.

#### Scenario: Sanitised ticket still maps
- **WHEN** a sanitised ticket is passed to the mapper
- **THEN** it maps to the same kind, status, parent key, domain, request drivers and effort as the unsanitised one

### Requirement: Raw data is never persisted
Raw Jira responses SHALL be held only in memory. Before writing, the check MUST scan the sanitised output for the Jira host name, e-mail addresses and the token, and MUST write nothing if any is found.

#### Scenario: Leak blocks writing
- **WHEN** a sanitised ticket still contains an e-mail address
- **THEN** no file is written and the report says why

### Requirement: Compatibility report
For each retrieved ticket the check SHALL run the mapper and report whether it mapped, the resulting kind, status, domain, request drivers, parent key, effort and whether a requester was found, together with the issue link direction texts, the Epic Link value shape and the sprint format observed. A ticket that cannot be mapped MUST be reported with the reason and MUST NOT stop the check.

#### Scenario: Task parent resolved
- **WHEN** the Task ticket has an Epic Link or a qualifying issue link
- **THEN** the report shows its parent key

#### Scenario: Unmapped ticket
- **WHEN** one ticket fails to map
- **THEN** the report lists the reason and the remaining tickets are still reported

### Requirement: Clear failure reporting
The check SHALL report authentication failure, missing ticket, timeout and connection failure each with a distinct, actionable message, and MUST exit with a non-zero status when any ticket could not be retrieved.

#### Scenario: Authentication failure
- **WHEN** Jira answers 401
- **THEN** the message says the token was rejected and does not show the token

#### Scenario: Ticket not found
- **WHEN** one requested key does not exist
- **THEN** it is reported as not found, the other tickets are still processed, and the exit status is non-zero
