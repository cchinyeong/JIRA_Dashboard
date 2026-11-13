import logging

import httpx
import pytest
from pydantic import SecretStr

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.services import connection_test as ct
from jira_dashboard.services.connection_test import check_connection
from jira_dashboard.utils.redaction import RedactingFilter

TOKEN = "pat-very-secret-0123456789"
ADDRESS = "https://jira.example.com"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


def run(handler, address: str = ADDRESS):
    return check_connection(
        get_settings(), address, SecretStr(TOKEN), transport=httpx.MockTransport(handler)
    )


def test_success_reports_the_display_name_and_uses_only_get_myself() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"displayName": "CY Chong", "name": "cchong"})

    result = run(handler)
    assert (result.ok, result.kind, result.user) == (True, ct.OK, "CY Chong")
    assert result.message == "Connected as CY Chong."
    assert [(r.method, r.url.path, r.url.host) for r in seen] == [
        ("GET", "/rest/api/2/myself", "jira.example.com")
    ]
    assert seen[0].headers["authorization"] == f"Bearer {TOKEN}"


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_token(status: int) -> None:
    result = run(lambda request: httpx.Response(status))
    assert (result.ok, result.kind) == (False, ct.REJECTED)
    assert "expired" in result.message and TOKEN not in result.message


def test_unreachable_for_connection_error_and_timeout() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    assert run(refuse).kind == ct.UNREACHABLE
    assert run(slow).kind == ct.UNREACHABLE


def test_certificate_problem() -> None:
    def untrusted(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("CERTIFICATE_VERIFY_FAILED", request=request)

    assert run(untrusted).kind == ct.CERTIFICATE


def test_other_http_error_and_unexpected_exception() -> None:
    other = run(lambda request: httpx.Response(500))
    assert (other.ok, other.kind) == (False, ct.OTHER)

    def broken(request: httpx.Request) -> httpx.Response:
        raise RuntimeError(f"boom {TOKEN}")

    result = run(broken)
    assert result.kind == ct.OTHER and TOKEN not in result.message


def test_nothing_secret_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.handler.addFilter(RedactingFilter())
    run(lambda request: httpx.Response(401))
    run(lambda request: httpx.Response(200, json={"displayName": "X"}))
    assert TOKEN not in caplog.text
    assert "Bearer" not in caplog.text
