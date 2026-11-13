import socket

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations import (
    JiraClient,
    JiraNotConfiguredError,
    JiraOnPremClient,
    map_issue,
)
from jira_dashboard.models import Project, Ticket, TicketStatus
from jira_dashboard.services import secrets


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://jira.example.com")
    return get_settings()


def test_abstract_client_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        JiraClient()


def test_fake_client_returns_tickets() -> None:
    ticket = Ticket("CAE-1", "s", Project("VE_CAE", "VE"), TicketStatus.NEW)

    class Fake(JiraClient):
        def get_ticket(self, key):
            return ticket

        def get_tickets(self, keys):
            return [ticket for _ in keys]

        def search_tickets(self, *, active_sprints_only=False):
            return [ticket]

    client: JiraClient = Fake()
    assert client.get_ticket("CAE-1") is ticket
    assert client.get_tickets(["CAE-1", "CAE-2"]) == [ticket, ticket]


def test_onprem_is_a_client(configured) -> None:
    assert isinstance(JiraOnPremClient(configured), JiraClient)


def test_placeholder_url_refused() -> None:
    with pytest.raises(JiraNotConfiguredError, match="jira.base_url"):
        JiraOnPremClient(get_settings())


def test_jql_scope(configured) -> None:
    client = JiraOnPremClient(configured)
    assert client.build_search_jql() == 'project = "VE_CAE" AND cf[12110] = "Structural Analysis"'
    assert client.build_search_jql(active_sprints_only=True).endswith("AND sprint in openSprints()")


def test_jql_escapes_quotes(configured) -> None:
    jira = configured.jira.model_copy(update={"team": 'Bad" OR project = X'})
    client = JiraOnPremClient(configured.model_copy(update={"jira": jira}))
    assert 'cf[12110] = "Bad\\" OR project = X"' in client.build_search_jql()


def test_skeleton_makes_no_network_or_secret_access(configured, monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("must not be called")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(secrets, "get_secret", forbidden)
    client = JiraOnPremClient(configured)
    with pytest.raises(NotImplementedError):
        client.get_ticket("CAE-1")
    with pytest.raises(NotImplementedError):
        client.get_tickets(["CAE-1"])
    with pytest.raises(NotImplementedError):
        client.search_tickets()


def test_public_exports() -> None:
    assert callable(map_issue)
