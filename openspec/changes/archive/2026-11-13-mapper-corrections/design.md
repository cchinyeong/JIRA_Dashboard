# Design

## Context

The live check (archived `jira-live-data-check`) returned real payloads for CAE-1513 (Epic), CAE-1558 (Risk), CAE-1592 (Issue) and CAE-1628 (Task), and the user clarified the hierarchy rules. Observed: CAE-1628 has an Epic Link and sits in a FUTURE sprint; CAE-1558 has three "Mention" links (two to Issues in project LDT, one from Task CAE-1559); the project key is `CAE` with name `VE_CAE`. On-prem parents and children are always in the same project; Jira Cloud may differ (MVP-9).

## Goals / Non-Goals

**Goals:**
- Parent relationships that match the real workflow and cannot be created by incidental ticket mentions.
- Configuration that states the rules instead of hiding them in code.
- Real payload shapes protected by regression tests.

**Non-Goals:**
- Cross-project parents for Jira Cloud (a single function holds the rule so MVP-9 can extend it).
- Reporting orphan tasks (service layer), the HTTP client, any UI.

## Decisions

- **Per-kind parent rules in `map_parent`:** a task uses the Epic Link, then qualifying links whose other end is a request type other than the Epic type (Risk, Issue); a Risk or Issue uses qualifying links whose other end has the Epic type; an Epic or any other kind has none. The target types derive from `issues.request_types` and `issues.epic_type`, not from literals. Alternative: one generic rule table in config; rejected as more machinery than three fixed relationships need.
- **Phrase lists split:** `issues.task_parent_phrases = ["is child of"]` and `issues.request_parent_phrases = ["is caused by"]`; `issues.epic_type = "Epic"`. The old `parent_link_phrases` is removed, not kept as an alias, because the model forbids unknown keys and a silent alias would hide the rule change. A stale local override fails loudly with the key named.
- **"mentions" excluded by omission,** plus a regression test built from the real CAE-1558 links (three Mention links, none produce a parent) and a test asserting `mentions` and `is mentioned by` are not defaults.
- **Same-project rule:** not added. On-prem guarantees it and the explicit phrases already exclude the cross-project "mentions" links. Cloud's cross-project parents would otherwise be blocked by it.
- **Task link to an Epic is not accepted:** Epics are reached only through the Epic Link, as stated by the user; a link-based Epic parent for tasks is ignored.
- **Project key:** `jira.project_key = "CAE"`; the query uses `project = "CAE"`.
- **Sprint scope:** `build_search_jql(in_sprints_only=...)` appends `AND sprint in (openSprints(), futureSprints())`; `search_tickets` in the interface and skeleton follow the rename. The sprint chosen by the mapper is unchanged (active first, otherwise highest id), which prefers a future sprint over a closed one.
- **Live fixtures as tests:** `tests/unit/test_live_fixtures.py` maps each file in `tests/unit/fixtures/live/` and asserts kinds, statuses, drivers and parents observed in the report (Epic and Risk and Issue are requests without parent; CAE-1628 is a task with parent CAE-1513). The module skips when the directory has no files, so a checkout without the sanitised fixtures still passes.

## Risks / Trade-offs

- [Removing `parent_link_phrases` breaks existing local overrides] → Only one local file exists today; the error names the key and `docs/configuration.md` states the new keys.
- [Phrases may differ for other work item types or Jira Cloud] → Phrases are configuration; Cloud is MVP-9.
- [CAE-1592 showed no links in the sample, so "Issue caused by Epic" is untested on real data] → Covered by a synthetic test from the stated rule; verify when a real Issue with an Epic link appears.
- [Live fixtures depend on the user's review before committing] → Tests skip when absent.
