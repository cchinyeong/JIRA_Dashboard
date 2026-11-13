# Spec Delta

## Purpose

Defines how the application talks to Jira Server over HTTP: read-only, authenticated, certificate-verified, resilient to transient failures, paged, and with errors a user can act on.

## ADDED Requirements

### Requirement: Read-only requests
The HTTP layer SHALL only issue GET requests and MUST NOT create, modify or transition anything in Jira.

#### Scenario: Every operation uses GET
- **WHEN** a ticket, several tickets and a search are retrieved through a recorded transport
- **THEN** every request made uses the GET method

### Requirement: Authentication and transport security
Requests SHALL authenticate with the stored personal access token as a bearer header and MUST NOT put it in a URL, log line or error message. TLS certificate verification MUST remain enabled and use the operating system's trusted certificates; there is no option to disable it.

#### Scenario: Token only in the header
- **WHEN** requests are made with a stored token
- **THEN** the token appears only in the authorization header

#### Scenario: Verification cannot be disabled
- **WHEN** the TLS context in use is inspected
- **THEN** certificate verification and host name checking are enabled

### Requirement: Classified errors
The HTTP layer SHALL report authentication rejection (401), access refusal (403), not found (404), timeout, connection failure, untrusted certificate and any other HTTP error status each with a distinct kind and an actionable message that never includes the token.

#### Scenario: Rejected token
- **WHEN** Jira answers 401
- **THEN** the error kind is authentication and the message says the token was rejected

#### Scenario: Untrusted certificate
- **WHEN** the connection fails certificate verification
- **THEN** the error kind is certificate and the message explains the corporate certificate authority

#### Scenario: Not found
- **WHEN** Jira answers 404 for a ticket
- **THEN** the error kind is not found

### Requirement: Bounded retry of transient failures
The HTTP layer SHALL retry a request after a timeout, a connection error, or HTTP status 429, 502, 503 or 504, up to the configured maximum number of retries with increasing delays. Authentication, access, not-found and other client errors MUST NOT be retried.

#### Scenario: Recovers after a transient error
- **WHEN** the first attempt answers 503 and the second answers 200
- **THEN** the request succeeds after one retry

#### Scenario: Retries exhausted
- **WHEN** every attempt answers 503 and the maximum retries is 2
- **THEN** exactly 3 attempts are made and the error reports the last cause

#### Scenario: Authentication failure not retried
- **WHEN** Jira answers 401
- **THEN** exactly one attempt is made

### Requirement: Paged search
Search results SHALL be retrieved page by page using the configured page size, until all results have been read. Retrieval MUST stop if a page returns no issues, so that it always terminates.

#### Scenario: Several pages
- **WHEN** a search matches 250 issues and the page size is 100
- **THEN** three requests are made and all 250 issues are returned

#### Scenario: Empty page ends the search
- **WHEN** Jira reports more results than it returns and a page comes back empty
- **THEN** retrieval stops with the issues received so far

### Requirement: Safe request logging
The HTTP layer SHALL log request method, path, status and duration, and MUST NOT log headers, tokens or response bodies.

#### Scenario: Token not logged
- **WHEN** requests succeed and fail with debug logging enabled
- **THEN** no log record contains the token
