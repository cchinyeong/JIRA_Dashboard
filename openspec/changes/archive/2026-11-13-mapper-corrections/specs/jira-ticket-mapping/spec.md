# Spec Delta

## MODIFIED Requirements

### Requirement: Parent mapping
The mapper SHALL set a ticket's parent key by kind. A task's parent is its Epic Link value, otherwise the Risk or Issue it is linked to by a configured task phrase (default "is child of"). A Risk or Issue's parent is the Epic it is linked to by a configured request phrase (default "is caused by"). Phrases are the direction text Jira shows for that ticket. "mentions" links MUST NOT define a parent. If several links qualify, the lowest key is used. Epics have no parent.

#### Scenario: Epic Link
- **WHEN** a task payload has an Epic Link value CAE-1513
- **THEN** the task's parent key is CAE-1513

#### Scenario: Issue link to a risk
- **WHEN** a task payload has no Epic Link and an issue link reading "is child of" to Risk ticket CAE-1558
- **THEN** the task's parent key is CAE-1558

#### Scenario: Task is child of an issue
- **WHEN** a task payload has no Epic Link and an issue link reading "is child of" to Issue ticket CAE-1592
- **THEN** the task's parent key is CAE-1592

#### Scenario: Risk caused by an epic
- **WHEN** a Risk payload has an issue link reading "is caused by" to Epic CAE-1513
- **THEN** the risk's parent key is CAE-1513

#### Scenario: Mentions never define a parent
- **WHEN** a Risk has links reading "mentions" to Issues in another project and "is mentioned by" a Task, and a Task has a link reading "mentions" a Risk
- **THEN** none of them has a parent key from those links

#### Scenario: Unrelated link ignored
- **WHEN** a task payload has no Epic Link and only a link reading "blocks" to a Risk ticket
- **THEN** the task has no parent key

#### Scenario: Wrong target type ignored
- **WHEN** a task has a link reading "is child of" to another Task or to an Epic
- **THEN** the task has no parent key from that link

#### Scenario: Several qualifying links
- **WHEN** a task is linked as "is child of" to CAE-1592 (Issue) and CAE-1558 (Risk)
- **THEN** the parent key is CAE-1558

#### Scenario: Request has no parent
- **WHEN** an Epic payload is mapped
- **THEN** its parent key is absent
