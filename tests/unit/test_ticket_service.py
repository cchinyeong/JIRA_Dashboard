import dataclasses
import logging
import subprocess
import sys
import threading
from datetime import UTC, datetime

import pytest

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations import JiraApiError, JiraClient, TicketBatch
from jira_dashboard.models import Project, Ticket, TicketKind, TicketStatus
from jira_dashboard.services.secrets import MissingSecretError
from jira_dashboard.services.ticket_query import TicketFilter
from jira_dashboard.services.ticket_service import (
    MAX_PARENT_ROUNDS,
    STATUS_BUSY,
    STATUS_FAILED,
    STATUS_OK,
    TicketService,
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://jira.example.com")


@pytest.fixture
def settings():
    return get_settings()


def make(key: str, parent: str | None = None, kind=TicketKind.TASK, **kwargs) -> Ticket:
    return Ticket(
        jira_key=key,
        summary=f"Summary of {key}",
        project=Project("CAE", "VE_CAE"),
        status=TicketStatus.NEW,
        kind=kind,
        parent_key=parent,
        jira_url=f"https://jira.example.com/browse/{key}",
        **kwargs,
    )


class FakeClient(JiraClient):
    def __init__(self, found=(), pool=()) -> None:
        self.calls: list[tuple] = []
        self.found = list(found)
        self.pool = {t.jira_key: t for t in pool}
        self.search_error: Exception | None = None
        self.parent_error: Exception | None = None
        self.search_gate: threading.Event | None = None
        self.search_started = threading.Event()

    def get_ticket(self, key):
        self.calls.append(("get_ticket", key))
        return self.pool[key]

    def get_tickets(self, keys):
        self.calls.append(("get_tickets", tuple(keys)))
        if self.parent_error:
            raise self.parent_error
        return TicketBatch([self.pool[k] for k in keys if k in self.pool])

    def search_tickets(self, *, in_sprints_only=False):
        self.calls.append(("search", in_sprints_only))
        self.search_started.set()
        if self.search_gate is not None:
            self.search_gate.wait(timeout=5)
        if self.search_error:
            raise self.search_error
        return TicketBatch(list(self.found))


def parent_calls(client: FakeClient) -> list[tuple]:
    return [call for call in client.calls if call[0] == "get_tickets"]


def test_parents_outside_the_search_are_loaded_but_not_listed(settings) -> None:
    epic = make("CAE-1513", kind=TicketKind.REQUEST)
    client = FakeClient([make("CAE-1628", "CAE-1513")], [epic])
    service = TicketService(client, settings)
    result = service.refresh()
    assert result.ok and result.ticket_count == 1 and result.parent_count == 1
    assert service.snapshot.get("CAE-1513").jira_key == "CAE-1513"
    assert [t.jira_key for t in service.list_tickets()] == ["CAE-1628"]
    assert client.calls == [("search", False), ("get_tickets", ("CAE-1513",))]


def test_parent_of_a_parent_is_loaded_over_rounds(settings) -> None:
    epic = make("CAE-1513", kind=TicketKind.REQUEST)
    risk = make("CAE-1558", "CAE-1513", kind=TicketKind.REQUEST)
    client = FakeClient([make("CAE-1628", "CAE-1558")], [risk, epic])
    result = TicketService(client, settings).refresh()
    assert result.ok and result.parent_count == 2
    assert parent_calls(client) == [
        ("get_tickets", ("CAE-1558",)),
        ("get_tickets", ("CAE-1513",)),
    ]


def test_missing_parent_still_succeeds_and_is_not_asked_again(settings) -> None:
    client = FakeClient([make("CAE-1", "CAE-404"), make("CAE-2", "CAE-404")])
    service = TicketService(client, settings)
    result = service.refresh()
    assert result.ok and result.parent_count == 0 and result.warnings == ()
    assert service.snapshot.get("CAE-404") is None
    assert parent_calls(client) == [("get_tickets", ("CAE-404",))]


def test_depth_limit_stops_the_rounds_with_a_warning(settings) -> None:
    chain = [make(f"CAE-{n}", f"CAE-{n + 1}", kind=TicketKind.REQUEST) for n in range(2, 8)]
    client = FakeClient([make("CAE-1", "CAE-2")], chain)
    result = TicketService(client, settings).refresh()
    assert result.ok and len(parent_calls(client)) == MAX_PARENT_ROUNDS
    assert result.parent_count == MAX_PARENT_ROUNDS
    assert any("deeper" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (JiraApiError("auth", "Jira rejected the token (401)."), "auth"),
        (JiraApiError("timeout", "Jira did not answer in time."), "timeout"),
        (JiraApiError("connection", "Cannot reach Jira."), "connection"),
        (JiraApiError("tls", "Certificate not trusted."), "tls"),
        (JiraApiError("http", "Jira answered with HTTP 500."), "http"),
        (MissingSecretError("jira-pat"), "no_token"),
    ],
)
def test_failures_become_results_not_exceptions(error, kind, settings) -> None:
    client = FakeClient()
    client.search_error = error
    result = TicketService(client, settings).refresh()
    assert result.status == STATUS_FAILED and not result.ok
    assert result.error_kind == kind and result.message == str(error)


def test_missing_token_message_explains_how_to_store(settings) -> None:
    client = FakeClient()
    client.search_error = MissingSecretError("jira-pat")
    assert "set_secret" in TicketService(client, settings).refresh().message


def test_unexpected_error_is_logged_and_reported(settings, caplog) -> None:
    client = FakeClient()
    client.search_error = RuntimeError("boom")
    with caplog.at_level(logging.ERROR, logger="jira_dashboard.services.ticket_service"):
        result = TicketService(client, settings).refresh()
    assert result.error_kind == "unexpected" and "boom" not in result.message
    assert "Traceback" in caplog.text and "boom" in caplog.text


def test_failed_refresh_keeps_previous_data(settings) -> None:
    client = FakeClient([make("CAE-1")])
    service = TicketService(client, settings)
    assert service.refresh().ok
    before = service.snapshot
    client.search_error = JiraApiError("auth", "Jira rejected the token (401).")
    result = service.refresh()
    assert result.error_kind == "auth"
    assert service.snapshot is before
    assert [t.jira_key for t in service.list_tickets()] == ["CAE-1"]


def test_first_refresh_failing_leaves_empty_data(settings) -> None:
    client = FakeClient()
    client.search_error = JiraApiError("timeout", "slow")
    service = TicketService(client, settings)
    assert not service.refresh().ok
    assert service.snapshot.tickets == () and service.snapshot.refreshed_at is None


@pytest.mark.parametrize(
    "error", [JiraApiError("timeout", "slow"), MissingSecretError("jira-pat"), RuntimeError("x")]
)
def test_parent_failure_is_only_a_warning(error, settings) -> None:
    client = FakeClient([make("CAE-1", "CAE-2")])
    client.parent_error = error
    service = TicketService(client, settings)
    result = service.refresh()
    assert result.status == STATUS_OK
    assert result.warnings and "Parent tickets could not be loaded" in result.warnings[0]
    assert [t.jira_key for t in service.list_tickets()] == ["CAE-1"]
    assert service.snapshot.warnings == result.warnings


def test_refresh_time_comes_from_the_clock(settings) -> None:
    when = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    service = TicketService(FakeClient([make("CAE-1")]), settings, clock=lambda: when)
    service.refresh()
    assert service.snapshot.refreshed_at == when
    assert service.summary().refreshed_at == when


def test_sprint_option_is_passed_to_the_client(settings) -> None:
    client = FakeClient()
    TicketService(client, settings).refresh(in_sprints_only=True)
    assert client.calls[0] == ("search", True)


def test_overlapping_refresh_is_refused_and_readers_see_old_data(settings) -> None:
    client = FakeClient([make("CAE-1")])
    service = TicketService(client, settings)
    assert service.refresh().ok
    old = service.snapshot

    client.found = [make("CAE-1"), make("CAE-2")]
    client.search_gate = threading.Event()
    client.search_started.clear()
    results = []
    worker = threading.Thread(target=lambda: results.append(service.refresh()))
    worker.start()
    assert client.search_started.wait(timeout=5)

    second = service.refresh()
    assert second.status == STATUS_BUSY and "already running" in second.message
    assert service.snapshot is old
    assert [t.jira_key for t in service.list_tickets()] == ["CAE-1"]

    client.search_gate.set()
    worker.join(timeout=5)
    assert results[0].ok
    assert [t.jira_key for t in service.list_tickets()] == ["CAE-1", "CAE-2"]
    assert len([call for call in client.calls if call[0] == "search"]) == 2


def test_facade_filter_group_and_summary(settings) -> None:
    epic = make("CAE-1513", kind=TicketKind.REQUEST)
    task = make("CAE-1628", "CAE-1513")
    service = TicketService(FakeClient([task, make("CAE-5")], [epic]), settings)
    service.refresh()
    view = service.grouped(service.list_tickets(TicketFilter(text="1628")))
    assert [n.ticket.jira_key for n in view.roots] == ["CAE-1513"]
    assert view.roots[0].children[0].ticket.jira_key == "CAE-1628"
    assert [t.jira_key for t in service.grouped().orphans] == ["CAE-5"]
    assert service.summary().total == 2
    assert "assignee" in service.facets()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://jira.example.com/browse/CAE-1", "https://jira.example.com/browse/CAE-1"),
        ("https://evil.example.net/browse/CAE-1", None),
        ("https://jira.example.com.evil.net/browse/CAE-1", None),
        ("http://jira.example.com/browse/CAE-1", None),
        ("javascript:alert(1)", None),
        ("/browse/CAE-1", None),
        ("", None),
        (None, None),
    ],
)
def test_ticket_link_only_for_the_configured_jira(url, expected, settings) -> None:
    service = TicketService(FakeClient(), settings)
    assert service.ticket_link(dataclasses.replace(make("CAE-1"), jira_url=url)) == expected


def test_service_calls_only_read_methods(settings) -> None:
    client = FakeClient([make("CAE-1", "CAE-2")], [make("CAE-2")])
    service = TicketService(client, settings)
    service.refresh()
    service.list_tickets()
    service.grouped()
    service.summary()
    assert {call[0] for call in client.calls} <= {"search", "get_tickets", "get_ticket"}


def test_services_import_without_any_gui_module() -> None:
    code = (
        "import sys; sys.modules['PySide6'] = None; sys.modules['PyQt6'] = None; "
        "import jira_dashboard.services.ticket_service as s; "
        "import jira_dashboard.services.ticket_query; "
        "assert not any(name.startswith(('PySide6', 'PyQt6')) for name in sys.modules "
        "if sys.modules[name] is not None)"
    )
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
