import logging
import ssl

import httpx
import pytest
from pydantic import SecretStr

from jira_dashboard.config import get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.integrations.jira_http import (
    JiraApiError,
    JiraHttp,
    build_ssl_context,
    check_fields,
    requested_fields,
    retry_delay,
)

TOKEN = "tok-secret-1234567890"
BODY = "SECRET-RESPONSE-BODY"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://jira.example.com")


@pytest.fixture
def settings():
    return get_settings()


def with_jira(settings, **updates):
    return settings.model_copy(update={"jira": settings.jira.model_copy(update=updates)})


def http_with(handler, settings, sleeps=None) -> JiraHttp:
    recorded = sleeps if sleeps is not None else []
    return JiraHttp(
        settings,
        SecretStr(TOKEN),
        transport=httpx.MockTransport(handler),
        sleep=recorded.append,
    )


def test_only_get_and_token_only_in_header(settings) -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"key": "CAE-1", "issues": [], "total": 0})

    http = http_with(handler, settings)
    http.get_issue("CAE-1")
    http.get_fields()
    list(http.search("project = CAE", ["summary"]))
    assert {request.method for request in seen} == {"GET"}
    for request in seen:
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert TOKEN not in str(request.url)


def test_requests_minimal_fields(settings) -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = request.url
        return httpx.Response(200, json={})

    http_with(handler, settings).get_issue("CAE-1558")
    assert captured["url"].path == "/rest/api/2/issue/CAE-1558"
    asked = captured["url"].params["fields"].split(",")
    assert asked == requested_fields(settings)
    assert "customfield_12112" in asked and "customfield_10001" in asked


def test_invalid_key_rejected(settings) -> None:
    http = http_with(lambda request: httpx.Response(200, json={}), settings)
    with pytest.raises(ValueError):
        http.get_issue("../../secret")


def test_tls_verification_enforced() -> None:
    context = build_ssl_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize(
    ("status", "kind", "text"),
    [
        (401, "auth", "rejected the token"),
        (403, "auth", "refused access"),
        (404, "not_found", "404"),
        (500, "http", "HTTP 500"),
    ],
)
def test_status_errors_are_not_retried(status, kind, text, settings) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status)

    with pytest.raises(JiraApiError) as info:
        http_with(handler, settings).get_issue("CAE-1")
    assert info.value.kind == kind
    assert text in str(info.value)
    assert TOKEN not in str(info.value)
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (httpx.ReadTimeout("slow"), "timeout"),
        (httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] bad"), "tls"),
        (httpx.ConnectError("refused"), "connection"),
        (httpx.ReadError("reset"), "connection"),
    ],
)
def test_transport_errors(error, kind, settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(JiraApiError) as info:
        http_with(handler, settings).get_issue("CAE-1")
    assert info.value.kind == kind
    assert TOKEN not in str(info.value)


def test_certificate_error_not_retried(settings) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] bad")

    with pytest.raises(JiraApiError):
        http_with(handler, settings).get_issue("CAE-1")
    assert len(calls) == 1


def test_recovers_after_transient_error(settings) -> None:
    answers = iter([503, 200])
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(answers)
        return httpx.Response(status, json={"key": "CAE-1"})

    result = http_with(handler, settings, sleeps).get_issue("CAE-1")
    assert result == {"key": "CAE-1"}
    assert sleeps == [retry_delay(0)]


def test_retries_exhausted_reports_last_cause(settings) -> None:
    calls = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(JiraApiError) as info:
        http_with(handler, settings, sleeps).get_issue("CAE-1")
    assert len(calls) == 3
    assert "503" in str(info.value)
    assert sleeps == [retry_delay(0), retry_delay(1)]


@pytest.mark.parametrize("error", [httpx.ReadTimeout("slow"), httpx.ConnectError("refused")])
def test_timeouts_and_connection_errors_are_retried(error, settings) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise error

    with pytest.raises(JiraApiError):
        http_with(handler, settings).get_issue("CAE-1")
    assert len(calls) == 3


def test_zero_retries_makes_one_attempt(settings) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(JiraApiError):
        http_with(handler, with_jira(settings, max_retries=0)).get_issue("CAE-1")
    assert len(calls) == 1


def test_retry_delay_grows_and_is_capped() -> None:
    assert retry_delay(0) < retry_delay(1) < retry_delay(2)
    assert retry_delay(20) == 5.0


def issues(count: int, start: int = 0) -> list[dict]:
    return [{"key": f"CAE-{n}"} for n in range(start, start + count)]


def test_search_pages_until_total(settings) -> None:
    total = 250
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        seen.append((params["startAt"], params["maxResults"]))
        start = int(params["startAt"])
        return httpx.Response(
            200, json={"issues": issues(min(100, total - start), start), "total": total}
        )

    result = list(http_with(handler, settings).search("project = CAE", ["summary"]))
    assert len(result) == 250
    assert seen == [("0", "100"), ("100", "100"), ("200", "100")]


def test_search_stops_on_empty_page(settings) -> None:
    pages = iter([{"issues": issues(100), "total": 300}, {"issues": [], "total": 300}])
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=next(pages))

    result = list(http_with(handler, settings).search("project = CAE", ["summary"]))
    assert len(result) == 100
    assert len(calls) == 2


def test_search_without_total_stops_on_short_page(settings) -> None:
    pages = iter([{"issues": issues(100)}, {"issues": issues(40, 100)}])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(pages))

    assert len(list(http_with(handler, settings).search("jql", ["summary"]))) == 140


def test_search_uses_configured_page_size(settings) -> None:
    sizes = []

    def handler(request: httpx.Request) -> httpx.Response:
        sizes.append(request.url.params["maxResults"])
        return httpx.Response(200, json={"issues": [], "total": 0})

    list(http_with(handler, with_jira(settings, page_size=25)).search("jql", ["summary"]))
    assert sizes == ["25"]


def test_logging_has_no_token_headers_or_bodies(settings, caplog) -> None:
    answers = iter([503, 200, 401])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(answers), json={"detail": BODY})

    http = http_with(handler, settings)
    with caplog.at_level(logging.DEBUG, logger="jira_dashboard.integrations.jira_http"):
        http.get_issue("CAE-1")
        with pytest.raises(JiraApiError):
            http.get_issue("CAE-2")
    text = caplog.text
    assert "GET /rest/api/2/issue/CAE-1 -> 200" in text
    assert "Retrying GET" in text
    assert TOKEN not in text and BODY not in text
    assert "authorization" not in text.lower() and "Bearer" not in text


def test_check_fields(settings) -> None:
    jira_fields = [
        {"id": "customfield_12110", "name": "Team"},
        {"id": "customfield_15253", "name": "Simulation Type"},
        {"id": "customfield_12112", "name": "Start of target"},
        {"id": "customfield_12113", "name": "Target end"},
        {"id": "customfield_10000", "name": "Sprint"},
        {"id": "timeoriginalestimate", "name": "Original Estimate"},
        {"id": "timeestimate", "name": "Remaining Estimate"},
        {"id": "components", "name": "Component/s"},
    ]
    findings = {f.setting: f for f in check_fields(settings, jira_fields)}
    assert findings["target_end"].status == "ok"
    assert findings["target_start"].status == "name_mismatch"
    assert findings["target_start"].jira_name == "Start of target"
    assert findings["epic_link"].status == "missing"
    assert findings["epic_link"].field_id == "customfield_10001"
    assert findings["sprint"].status == "ok"


def test_dyson_project_field_is_requested_and_checked(settings) -> None:
    assert "customfield_12901" in requested_fields(settings)
    findings = {
        f.setting: f
        for f in check_fields(settings, [{"id": "customfield_12901", "name": "Dyson Project List"}])
    }
    assert findings["dyson_project_list"].status == "ok"
    renamed = check_fields(settings, [{"id": "customfield_12901", "name": "Something else"}])
    assert {f.setting: f.status for f in renamed}["dyson_project_list"] == "name_mismatch"
    missing = {f.setting: f for f in check_fields(settings, [])}
    assert missing["dyson_project_list"].status == "missing"
