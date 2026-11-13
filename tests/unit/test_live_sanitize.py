import copy
import json
from pathlib import Path

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.jira_mapping import map_issue
from jira_dashboard.integrations.live_sanitize import (
    UserAliases,
    find_leaks,
    sanitize_description,
    sanitize_issue,
)

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_NAMES = ["issue_cae_1558.json", "task_epic_link.json", "task_risk_link.json"]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


@pytest.fixture
def settings():
    return get_settings()


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_users_replaced_consistently(settings) -> None:
    payload = load("issue_cae_1558.json")
    payload["fields"]["reporter"] = {"name": "other", "displayName": "Someone Else"}
    clean = sanitize_issue(payload, settings, UserAliases())["fields"]
    assert clean["assignee"]["name"] == "user-1"
    assert clean["reporter"]["name"] == "user-2"
    text = json.dumps(clean)
    assert "cchong" not in text and "CY Chong" not in text and "cy.chong" not in text


def test_same_person_same_alias(settings) -> None:
    payload = load("issue_cae_1558.json")
    clean = sanitize_issue(payload, settings, UserAliases())["fields"]
    assert clean["assignee"] == clean["reporter"]


def test_free_text_removed(settings) -> None:
    clean = sanitize_issue(load("issue_cae_1558.json"), settings, UserAliases())["fields"]
    assert clean["summary"] == "Sample ticket CAE-1558"
    assert clean["description"] == (
        "{panel:title=PIC (Requester - Full Name)}\nPerson A.\n{panel}\n"
        "{panel:title=Background}\n<redacted>\n{panel}\n"
        "{panel:title=Conclusion}\n<redacted>\n{panel}"
    )
    assert "Mohamad" not in json.dumps(clean)


def test_description_without_panels_is_redacted(settings) -> None:
    assert sanitize_description("secret text", settings.requester.panel_title) == "<redacted>"
    assert sanitize_description(None, settings.requester.panel_title) is None


def test_unknown_fields_and_urls_dropped(settings) -> None:
    payload = load("issue_cae_1558.json")
    payload["self"] = "https://jira.example.com/rest/api/2/issue/1"
    payload["fields"]["customfield_77777"] = "secret"
    payload["fields"]["watches"] = {"self": "https://jira.example.com/x"}
    payload["fields"]["assignee"]["avatarUrls"] = {"48x48": "https://jira.example.com/a.png"}
    clean = sanitize_issue(payload, settings, UserAliases())
    text = json.dumps(clean)
    assert "customfield_77777" not in text
    assert "watches" not in text
    assert "avatar" not in text
    assert "http" not in text
    assert set(clean) == {"key", "fields"}


def test_links_keep_structure_only(settings) -> None:
    payload = load("task_risk_link.json")
    payload["fields"]["issuelinks"][0]["inwardIssue"]["fields"]["summary"] = "Secret title"
    clean = sanitize_issue(payload, settings, UserAliases())["fields"]["issuelinks"]
    assert clean[0]["type"]["inward"] == "is child of"
    assert clean[0]["inwardIssue"] == {
        "key": "CAE-1558",
        "fields": {"issuetype": {"name": "Risk"}},
    }
    assert "Secret" not in json.dumps(clean)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_sanitised_ticket_maps_the_same(name, settings) -> None:
    raw = load(name)
    before = copy.deepcopy(raw)
    clean = sanitize_issue(raw, settings, UserAliases())
    assert raw == before
    original, cleaned = map_issue(raw, settings), map_issue(clean, settings)
    for attribute in (
        "jira_key",
        "kind",
        "status",
        "parent_key",
        "domain",
        "request_drivers",
        "estimated_effort",
        "remaining_effort",
        "target_start_date",
        "target_end_date",
        "sprint",
        "issue_type",
        "priority",
    ):
        assert getattr(cleaned, attribute) == getattr(original, attribute), attribute
    assert (cleaned.requester is None) == (original.requester is None)


def test_leak_scan_categories_without_echo() -> None:
    text = '{"a": "bob@corp.com", "b": "https://jira.corp.example/x", "c": "tok-123456"}'
    leaks = find_leaks(text, "https://jira.corp.example", "tok-123456")
    assert leaks == ["Jira host name", "e-mail address", "token"]
    assert all("bob" not in leak and "tok-" not in leak for leak in leaks)


def test_leak_scan_allows_example_domain_and_clean_text() -> None:
    assert find_leaks('"user-1@example.com"', "https://jira.corp.example", "tok-123456") == []
