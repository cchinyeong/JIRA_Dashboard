# Spec Delta

## MODIFIED Requirements

### Requirement: Status bar summary
The status bar SHALL show the number of tickets, the time of the last successful refresh, the number of unreadable tickets and the number of tickets with findings. While a filter is active it SHALL show the number of tickets shown out of the total.

#### Scenario: After a refresh
- **WHEN** a refresh succeeds with 353 tickets, 73 with findings and none unreadable
- **THEN** the status bar shows those counts and the refresh time

#### Scenario: Filter active
- **WHEN** a filter leaves 40 of 353 tickets
- **THEN** the status bar shows "40 of 353 tickets"
