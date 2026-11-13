# Spec Delta

## Purpose

Defines the read-only details panel that shows everything the application knows about the ticket selected in the main table, including its data-quality findings and its place in the hierarchy.

## ADDED Requirements

### Requirement: Details for the selected ticket
The window SHALL show a details panel beside the ticket table. When a ticket is selected, the panel SHALL show its key, summary, status, type, priority, domain, request drivers, assignee, reporter, requester, sprint, target start and end dates, actual start and completion dates, created and updated dates, estimated and remaining effort in days, and blocked reason. The panel MUST be read-only.

#### Scenario: Ticket selected
- **WHEN** the user selects a ticket in the table
- **THEN** the panel shows that ticket's values, with dates as day, month name and year and effort in days

#### Scenario: Nothing selected
- **WHEN** no ticket is selected
- **THEN** the panel shows a hint to select a ticket and no ticket values

#### Scenario: Unknown values
- **WHEN** the selected ticket has no requester, sprint, dates or estimate
- **THEN** those values read "Unknown" in the unknown style and nothing is guessed

#### Scenario: Non-standard status
- **WHEN** the selected ticket has the unknown status with raw name "Implemented"
- **THEN** the panel shows "Unknown (Implemented)" as its status

### Requirement: Sprint and blocked detail
The panel SHALL show the sprint's name, state and dates, and SHALL show when the ticket is blocked together with the blocked reason when there is one.

#### Scenario: Sprint with dates
- **WHEN** the selected ticket is in an active sprint with a start and end date
- **THEN** the panel shows the sprint name, its state and its dates

#### Scenario: Blocked ticket
- **WHEN** the selected ticket is in the Refinement status
- **THEN** the panel shows that it is blocked

### Requirement: Hierarchy
The panel SHALL show the ticket's parent key. When the parent is loaded, it SHALL also show the parent's summary and type.

#### Scenario: Parent loaded
- **WHEN** the selected ticket's parent is in the latest refresh data
- **THEN** the panel shows the parent key, its type and its summary

#### Scenario: Parent not loaded
- **WHEN** the selected ticket has a parent key whose ticket was not loaded
- **THEN** the panel shows the parent key alone

#### Scenario: No parent
- **WHEN** the selected ticket has no parent
- **THEN** the panel shows the parent as "None"

### Requirement: Findings in full
The panel SHALL list every finding of the selected ticket with its message, the field it concerns, the related ticket when there is one, and the suggested correction. A ticket without findings SHALL show that no findings were detected.

#### Scenario: Ticket with findings
- **WHEN** a Task without a parent is selected
- **THEN** the panel lists the finding with its message and suggested correction

#### Scenario: Ticket without findings
- **WHEN** a ticket without findings is selected
- **THEN** the panel says no findings were detected

### Requirement: Description shown formatted and safely
The panel SHALL show the description with Jira wiki markup converted to readable formatting, so that formatting codes such as panel, colour and heading markers do not appear as text. Text that is not Jira markup, including HTML tags, MUST be shown literally and never interpreted. The panel MUST NOT load images or follow links from the description. An empty description SHALL read "Unknown".

#### Scenario: Jira markup in description
- **WHEN** a description contains a panel with a title, bold text and a list
- **THEN** the panel shows the title as a heading, the text bold and the list items, without the markup codes

#### Scenario: Images and links
- **WHEN** a description contains an image and a link with a web address
- **THEN** the image is shown as its file name in brackets, the link as its text followed by its address, and nothing is loaded or opened

#### Scenario: HTML in description
- **WHEN** a description contains HTML tags or a script
- **THEN** the characters are shown literally and nothing is rendered or executed

### Requirement: Open in Jira from the panel
The panel SHALL have an Open in Jira button that opens only the link the ticket service allows, and that is disabled when there is none or no ticket is selected.

#### Scenario: Allowed link
- **WHEN** the user presses the button with an allowed ticket selected
- **THEN** that link is opened

#### Scenario: No link
- **WHEN** the service gives no link for the selected ticket
- **THEN** the button is disabled

### Requirement: Selection across refresh
After a refresh, the panel SHALL keep showing the selected ticket, updated to the new data, when that ticket is still in the table; otherwise the panel SHALL return to its empty state.

#### Scenario: Ticket still present
- **WHEN** a refresh finishes and the selected ticket is still in the data
- **THEN** it stays selected and the panel shows its new values

#### Scenario: Ticket gone
- **WHEN** a refresh finishes and the selected ticket is no longer in the data
- **THEN** the selection is cleared and the panel shows its hint
