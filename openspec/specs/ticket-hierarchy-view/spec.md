# ticket-hierarchy-view Specification

## Purpose
Defines the hierarchy view that shows requests (Epics, Risks and Issues) with their Tasks beneath, and makes Tasks without a parent visible, as an alternative to the flat ticket table.

## Requirements

### Requirement: Table and hierarchy views
The window SHALL offer a view switch between the flat table and a hierarchy tree. Both views MUST use the same filter and the same details panel.

#### Scenario: Switching view
- **WHEN** the user switches to Hierarchy
- **THEN** the tickets are shown as a tree and the filter bar still applies

#### Scenario: Shared selection
- **WHEN** the user selects a ticket in the tree
- **THEN** the details panel shows it, and Open in Jira acts on it as in the table

### Requirement: Tasks beneath their parents
The hierarchy view SHALL show each Task beneath its parent request, following the parent relation the application derived, and SHALL show requests as top-level entries unless they have a loaded parent.

#### Scenario: Task under its Epic
- **WHEN** a Task's parent is an Epic in the data
- **THEN** the Task appears beneath that Epic

#### Scenario: Request with several tasks
- **WHEN** a request has three Tasks
- **THEN** all three are listed beneath it in key order

### Requirement: Context parents shown dimmed
When a ticket matches the filter but its parent does not, or its parent was loaded only for context, the parent SHALL still be shown, dimmed, so that the structure remains visible. Dimmed entries MUST be distinguishable from matching ones and MUST NOT count as matches.

#### Scenario: Parent does not match
- **WHEN** a filter matches a Task but not its Epic
- **THEN** the Epic is shown dimmed above the Task

### Requirement: Tasks without a parent
The hierarchy view SHALL list Tasks that have no parent under a separate top-level entry named "Tasks without a parent" with their count, and the entry MUST be absent when there are none.

#### Scenario: Orphan tasks
- **WHEN** 61 Tasks have no parent
- **THEN** a "Tasks without a parent (61)" entry lists them

#### Scenario: No orphan tasks
- **WHEN** every Task has a parent
- **THEN** no such entry is shown

### Requirement: Hierarchy columns and expansion
Each hierarchy row SHALL show the key with the summary, type, status, assignee, sprint, target end date and finding count, with unknown values and findings styled as in the table. The tree SHALL be expanded when first shown, and the expansion MAY be reset by a refresh.

#### Scenario: Row content
- **WHEN** a Task with a finding is shown in the tree
- **THEN** its row shows the finding count and the same tint and tooltip as in the table

### Requirement: View survives refresh
The chosen view and the selected ticket SHALL be kept across a refresh when the ticket still exists.

#### Scenario: Refresh in hierarchy view
- **WHEN** a refresh finishes while the hierarchy view is shown
- **THEN** the hierarchy view stays shown with the new data
