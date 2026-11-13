# Spec Delta

## Purpose

Defines how credentials such as the Jira Personal Access Token are stored and retrieved outside source code and settings files, and how they are protected in memory and in output.

## ADDED Requirements

### Requirement: Secure credential storage
The system SHALL store and retrieve credentials through the Windows Credential Manager by default, under a single application-specific service name.

#### Scenario: Round trip
- **WHEN** a secret is stored under a name and then retrieved
- **THEN** the retrieved value equals the stored value

#### Scenario: Deletion
- **WHEN** a stored secret is deleted
- **THEN** a later retrieval reports it as missing

### Requirement: Secrets masked when printed
Retrieved secrets SHALL be returned in a form that does not reveal the value when converted to text, shown in a representation, or included in a log message.

#### Scenario: Representation hides value
- **WHEN** a retrieved secret is converted to text or its representation
- **THEN** the value is not shown

#### Scenario: Explicit reveal
- **WHEN** code explicitly requests the underlying value
- **THEN** the real value is returned

### Requirement: Missing secrets are explicit
Retrieving a secret that does not exist SHALL fail with a specific error that names the secret and explains how to store it, and MUST NOT return an empty value.

#### Scenario: Missing secret
- **WHEN** a secret that was never stored is retrieved
- **THEN** a missing-secret error naming the secret is raised

### Requirement: Development-only environment fallback
The system SHALL support an environment variable fallback for secrets that is used only when explicitly enabled, and the stored credential MUST take precedence when both exist.

#### Scenario: Fallback disabled by default
- **WHEN** the environment variable for a secret is set but the fallback is not enabled and no stored secret exists
- **THEN** a missing-secret error is raised

#### Scenario: Fallback enabled
- **WHEN** the fallback is enabled and no stored secret exists
- **THEN** the environment value is returned

### Requirement: Secrets registered for redaction
Every secret retrieved SHALL be registered so that its value is masked in subsequent log output.

#### Scenario: Retrieved secret redacted
- **WHEN** a secret is retrieved and later appears in a log message
- **THEN** the log output masks it

### Requirement: Secrets are never persisted in settings or source
Credentials MUST NOT be written to settings files, source code, or the repository.

#### Scenario: Storing does not touch files
- **WHEN** a secret is stored
- **THEN** no settings or project file is created or modified
