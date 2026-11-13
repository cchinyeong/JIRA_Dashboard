# dashboard-window Specification

## Purpose
Defines the application's main window: how it starts, shows the team's tickets in a sortable table, refreshes them without freezing, highlights data-quality findings and opens tickets in Jira, all read-only.

## Requirements

### Requirement: Application start
Running the application SHALL open the main window and start a refresh automatically. The window MUST appear before the refresh finishes.

#### Scenario: Automatic first refresh
- **WHEN** the application starts and Jira is configured
- **THEN** the window is shown and a refresh begins without user action

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

### Requirement: Ticket table
The window SHALL show the tickets of the latest refresh in a read-only table with the columns Key, Summary, Type, Status, Priority, Assignee, Domain, Sprint, Target end, Remaining (days), Findings and Updated. A missing value MUST be shown as "Unknown" in a visibly different style, and MUST NOT be guessed.

#### Scenario: Known values
- **WHEN** a ticket has all values
- **THEN** each column shows its value, with dates as day, month name and year and remaining effort in days

#### Scenario: Unknown values
- **WHEN** a ticket has no assignee, sprint or estimate
- **THEN** those cells read "Unknown" in the unknown style

#### Scenario: Non-standard status
- **WHEN** a ticket has the unknown status with raw name "Implemented"
- **THEN** its status cell reads "Unknown (Implemented)"

#### Scenario: Read-only
- **WHEN** the user tries to edit a cell
- **THEN** nothing changes

### Requirement: Sorting
Clicking a column header SHALL sort the table by that column, clicking again SHALL reverse it. The default order is by ticket key numerically. Unknown values MUST sort after known ones in both directions.

#### Scenario: Default order
- **WHEN** the table is first shown
- **THEN** CAE-99 appears before CAE-100

#### Scenario: Unknown last
- **WHEN** the table is sorted by assignee in either direction
- **THEN** tickets without an assignee come last

### Requirement: Findings indicator
Tickets with findings SHALL show the number of findings in the Findings column, a tinted row, and a tooltip that lists each finding's message and suggestion.

#### Scenario: Ticket with findings
- **WHEN** a Task has a parent finding
- **THEN** its Findings cell shows 1, its row is tinted, and its tooltip describes the finding

#### Scenario: Ticket without findings
- **WHEN** a ticket has no findings
- **THEN** its Findings cell is empty and its row is not tinted

### Requirement: Responsive manual refresh
A Refresh button and the F5 key SHALL start a refresh on a background thread so that the window stays responsive. The button MUST be disabled and a progress indication shown while a refresh runs.

#### Scenario: Refresh in progress
- **WHEN** the user presses Refresh
- **THEN** the button is disabled and a busy indication is shown until the result arrives

#### Scenario: Refresh finished
- **WHEN** the refresh succeeds
- **THEN** the table shows the new data and the button is enabled again

### Requirement: Refresh failures keep the data
When a refresh fails, the table SHALL keep the previous data and the window SHALL show a banner with the failure message. When a refresh reports warnings, they MUST be shown.

#### Scenario: Failed refresh
- **WHEN** a refresh fails after an earlier success
- **THEN** the earlier tickets stay in the table and a banner shows the readable message

#### Scenario: Warning
- **WHEN** a refresh succeeds with a warning that parents could not be loaded
- **THEN** the warning is shown

#### Scenario: Banner cleared
- **WHEN** a later refresh succeeds
- **THEN** the failure banner is removed

### Requirement: Status bar summary
The status bar SHALL show the number of tickets, the time of the last successful refresh, the number of unreadable tickets and the number of tickets with findings. While a filter is active it SHALL show the number of tickets shown out of the total.

#### Scenario: After a refresh
- **WHEN** a refresh succeeds with 353 tickets, 73 with findings and none unreadable
- **THEN** the status bar shows those counts and the refresh time

#### Scenario: Filter active
- **WHEN** a filter leaves 40 of 353 tickets
- **THEN** the status bar shows "40 of 353 tickets"

### Requirement: Open in Jira
The window SHALL open the selected ticket in the web browser through a toolbar action, a context menu entry and a double-click. It MUST open only the link the ticket service allows, and the action MUST be unavailable when there is none.

#### Scenario: Allowed link
- **WHEN** the user double-clicks a ticket whose link belongs to the configured Jira
- **THEN** that link is opened

#### Scenario: Refused link
- **WHEN** the ticket service gives no link for the selected ticket
- **THEN** nothing is opened and the action is disabled

### Requirement: No Jira access on the interface thread
The window MUST NOT call Jira or the Jira client directly and MUST call the ticket service's refresh only from a background thread.

#### Scenario: Interface thread stays free
- **WHEN** a refresh is running
- **THEN** the interface thread is not blocked and can handle input
