# Spec Delta

## MODIFIED Requirements

### Requirement: Jira not configured
When the Jira address is not configured or no token is stored, the window SHALL say what is missing, MUST NOT crash or show a technical error, and SHALL open the Jira setup dialog so the user can configure it. The window MUST also offer a "Jira setup…" action at any time.

#### Scenario: Placeholder address
- **WHEN** the application starts with the placeholder Jira address
- **THEN** the window shows a message naming what to configure and no table data, and the setup dialog opens

#### Scenario: No token stored
- **WHEN** the first refresh reports that no token is stored
- **THEN** the window shows that message and offers the setup dialog

#### Scenario: Setup completed
- **WHEN** the user saves valid settings in the dialog
- **THEN** the message disappears and a refresh starts
