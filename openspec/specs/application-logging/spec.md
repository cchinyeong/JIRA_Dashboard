# application-logging Specification

## Purpose
Defines how the application configures its logs, including rotation and automatic redaction of credentials, so that diagnostics are available without leaking secrets.

## Requirements

### Requirement: Configured logging
The system SHALL configure logging from the logging settings, using the configured level and writing to both the console and a log file in the configured directory.

#### Scenario: Level applied
- **WHEN** logging is configured with level DEBUG
- **THEN** debug messages are emitted

#### Scenario: File created
- **WHEN** logging is configured and a message is logged
- **THEN** the message appears in a file inside the configured log directory

### Requirement: Log rotation
The system SHALL rotate log files by size and keep a bounded number of backups.

#### Scenario: Bounded files
- **WHEN** the log file exceeds the configured maximum size
- **THEN** it is rotated and no more than the configured number of backups are kept

### Requirement: Idempotent setup
Configuring logging more than once SHALL NOT duplicate output.

#### Scenario: Repeated setup
- **WHEN** logging is configured twice and one message is logged
- **THEN** the message appears once per destination

### Requirement: Credential redaction
The system MUST mask credentials in all log output, including Bearer and Basic authorisation values, `Authorization` headers, `token`, `password` and `secret` key-value pairs, and any secret value registered for redaction.

#### Scenario: Bearer token masked
- **WHEN** a message containing `Authorization: Bearer abc123` is logged
- **THEN** the output does not contain `abc123`

#### Scenario: Formatted argument masked
- **WHEN** a registered secret value is passed as a logging argument
- **THEN** the output does not contain the secret value

#### Scenario: Exception text masked
- **WHEN** an exception whose text contains a registered secret is logged with its traceback
- **THEN** the output does not contain the secret value
