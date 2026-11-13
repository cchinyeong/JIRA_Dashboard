# Spec Delta

## ADDED Requirements

### Requirement: Dyson project mapping
The mapper SHALL map the multi-select field "Dyson Project List", read through its configured field ID, to the ticket's list of Dyson projects, using each selected option's name. Blank names MUST be dropped and repeated names kept once. A ticket whose field is empty or absent MUST get an empty list, and the mapper MUST NOT guess a project.

#### Scenario: Several projects
- **WHEN** the payload's field holds the options `898B` and `915`
- **THEN** the ticket's Dyson projects are `898B` and `915`

#### Scenario: Field empty
- **WHEN** the payload's field is null or an empty list
- **THEN** the ticket has no Dyson projects

#### Scenario: Reconfigured field ID
- **WHEN** the configured Dyson project field ID is changed and the payload uses the new ID
- **THEN** the ticket carries the projects from the new field
