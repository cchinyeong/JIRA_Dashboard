# Jira integration

All Jira access goes through `jira_dashboard.integrations.JiraClient`. It returns internal `Ticket` models only; nothing outside `integrations` sees Jira payloads. `JiraOnPremClient` implements it for Jira Server. A `JiraCloudClient` can replace it later without changes elsewhere.

## Current state (MVP-0)

- `JiraOnPremClient` is a skeleton: it refuses to be created while `jira.base_url` is still the placeholder, builds the team-scoped query, and its read methods (`get_ticket`, `get_tickets`, `search_tickets`) raise `NotImplementedError`. It makes no network calls and reads no credentials.
- `map_issue(payload, settings)` converts a Jira Server issue (REST v2 JSON) into a `Ticket`. It is pure and raises `TicketMappingError` naming the ticket when a payload cannot be mapped (for example an unsupported status).

## Query scope

`build_search_jql()` gives `project = "VE_CAE" AND cf[12110] = "Structural Analysis"`, plus `AND sprint in openSprints()` for active sprints only. Values are quoted and escaped.

## Ticket hierarchy

Epic, Risk and Issue tickets are requests (`TicketKind.REQUEST`); Tasks (`TicketKind.TASK`) are the sprint work and belong to one request:

- Epic: the Epic Link field (`customfield_10001`), because these Epics are not Jira containers.
- Risk or Issue: an issue link whose text on the Task matches `issues.parent_link_phrases` (default `is child of`, `is caused by`) and whose other end is a Risk or Issue. If several qualify, the lowest key is used.

A Task's requester is not inherited in the mapper; each ticket's own description panel is read.

## Payload quirks handled

- Effort arrives in seconds and becomes days (`working_time.hours_per_day`).
- Sprint is a list of legacy strings (`...Sprint@hash[id=12,state=ACTIVE,name=...]`) or structured objects; the active sprint is chosen.
- Domain comes from the Simulation Type select field, request drivers from Components.
- Timestamps carry offsets such as `+0800`.

## Still to verify against a live Jira (MVP-1)

The mapper was built from screenshots and Jira Server documentation, not a real response. Before relying on it, compare real payloads for: the direction texts in `issuelinks`, the shape of the Epic Link value, the sprint string, and the field IDs in `docs/configuration.md`. List the link phrases found on real Tasks and decide which ones mean "belongs to".
