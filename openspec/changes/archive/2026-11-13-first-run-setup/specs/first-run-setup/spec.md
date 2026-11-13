# Spec Delta

## Purpose

Defines the setup dialog that lets a user enter the Jira address and Personal Access Token, test the connection, and save them securely, so the dashboard can be configured from inside the application.

## ADDED Requirements

### Requirement: Setup dialog
The application SHALL provide a Jira setup dialog with a field for the Jira address and a masked field for the Personal Access Token. It SHALL open automatically at start when the Jira address is the placeholder or no token is stored, and SHALL be available at any time from the window. The dialog MUST be modal and MUST NOT change anything until the user saves.

#### Scenario: First run
- **WHEN** the application starts with the placeholder address and no stored token
- **THEN** the setup dialog opens

#### Scenario: Opened later
- **WHEN** the user chooses "Jira setup…" in a configured application
- **THEN** the dialog opens showing the current address and that a token is stored, without showing the token

#### Scenario: Cancel
- **WHEN** the user cancels the dialog
- **THEN** the address, the stored token and the window are unchanged

### Requirement: Address validation
The dialog SHALL accept an address only if it uses `https`, has a host, and has no user name, password, query, fragment or path beyond a single trailing slash. It MUST show a readable reason for a rejected address and MUST NOT save it. A trailing slash SHALL be removed before saving.

#### Scenario: Valid address
- **WHEN** the user enters `https://jira.example.com/`
- **THEN** the address is accepted and stored as `https://jira.example.com`

#### Scenario: Insecure address
- **WHEN** the user enters `http://jira.example.com`
- **THEN** the dialog rejects it, explains that https is required, and Save stays unavailable

#### Scenario: Address with credentials
- **WHEN** the user enters `https://user:secret@jira.example.com`
- **THEN** the dialog rejects it without echoing the secret part

#### Scenario: Placeholder address
- **WHEN** the user enters the placeholder host
- **THEN** the dialog rejects it as not a real Jira address

### Requirement: Token handling
The token field MUST mask what is typed. The token MUST NOT be written to any file, logged, shown in a message or kept after saving, and MUST be stored only in Windows Credential Manager through the secret store. When a token is already stored and the field is left empty, the stored token SHALL be kept.

#### Scenario: Token stored
- **WHEN** the user saves a new token
- **THEN** it is stored in the secret store, appears in no file, and the dialog's field is cleared

#### Scenario: Keep stored token
- **WHEN** a token is stored and the user saves a changed address with the token field empty
- **THEN** the address changes and the stored token is unchanged

#### Scenario: No token available
- **WHEN** no token is stored and the token field is empty
- **THEN** Save is unavailable

### Requirement: Connection test
A Test connection button SHALL make one read-only request to the entered address with the entered token, or the stored one when the field is empty, on a background thread, and SHALL report the outcome in plain words: connected as the user's display name, address unreachable, certificate problem, token rejected, or another failure. The test MUST NOT save anything and MUST NOT write to Jira.

#### Scenario: Successful test
- **WHEN** the test succeeds
- **THEN** the dialog shows that it connected as the user's display name

#### Scenario: Token rejected
- **WHEN** Jira answers that the token is not accepted
- **THEN** the dialog says the token was rejected and suggests checking its expiry, without showing the token

#### Scenario: Unreachable address
- **WHEN** the address cannot be reached
- **THEN** the dialog says so and the dialog stays responsive during the attempt

### Requirement: Saving
Save SHALL store the token when one was entered, then write only the address into the local settings file, keeping the rest of that file, through a temporary file and an atomic replace so that a failure leaves the previous file intact. After a successful save the window SHALL use the new settings without a restart and start a refresh. Saving without a successful test SHALL require the user to confirm.

#### Scenario: Settings file updated
- **WHEN** the local settings file has other settings and a comment and the user saves a new address
- **THEN** only the Jira address line changes

#### Scenario: No settings file yet
- **WHEN** no local settings file exists and the user saves an address
- **THEN** the file is created with that address

#### Scenario: Write fails
- **WHEN** writing the settings file fails
- **THEN** the previous file is unchanged, the dialog stays open and shows the reason

#### Scenario: Applied without restart
- **WHEN** the user saves valid settings
- **THEN** the window starts a refresh with the new address and token and no restart is needed
