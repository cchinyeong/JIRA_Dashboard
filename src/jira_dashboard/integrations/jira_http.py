import logging
import re
import ssl
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
import truststore
from pydantic import SecretStr

from jira_dashboard.config.settings import Settings

logger = logging.getLogger(__name__)

KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]+-\d+")
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
BASE_DELAY_SECONDS = 0.5
MAX_DELAY_SECONDS = 5.0
ISSUE_FIELDS = (
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "reporter",
    "created",
    "updated",
    "project",
    "issuelinks",
)
FIELD_NAME_HINTS = {
    "team": "team",
    "simulation_type": "simulation",
    "target_start": "target start",
    "target_end": "target end",
    "sprint": "sprint",
    "epic_link": "epic link",
    "dyson_project_list": "dyson project",
}


class JiraApiError(Exception):
    def __init__(self, kind: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


@dataclass(frozen=True)
class FieldFinding:
    setting: str
    field_id: str
    status: str
    jira_name: str | None = None


def build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def requested_fields(settings: Settings) -> list[str]:
    ids = settings.fields
    configured = [
        ids.request_drivers,
        ids.simulation_type,
        ids.target_start,
        ids.target_end,
        ids.sprint,
        ids.estimated_effort,
        ids.remaining_effort,
    ]
    if ids.epic_link:
        configured.append(ids.epic_link)
    if ids.dyson_project_list:
        configured.append(ids.dyson_project_list)
    return list(dict.fromkeys([*ISSUE_FIELDS, *configured]))


def retry_delay(attempt: int) -> float:
    return min(BASE_DELAY_SECONDS * 2**attempt, MAX_DELAY_SECONDS)


class JiraHttp:
    """Read-only Jira Server access; every request goes through _get_once."""

    def __init__(
        self,
        settings: Settings,
        token: SecretStr,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=settings.jira.base_url,
            headers={
                "Authorization": f"Bearer {token.get_secret_value()}",
                "Accept": "application/json",
            },
            timeout=settings.jira.timeout_seconds,
            verify=build_ssl_context(),
            transport=transport,
        )
        self._settings = settings
        self._max_retries = settings.jira.max_retries
        self._page_size = settings.jira.page_size
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        attempt = 0
        while True:
            try:
                return self._get_once(path, params)
            except JiraApiError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
                delay = retry_delay(attempt)
                attempt += 1
                logger.warning("Retrying GET %s in %.1f s after %s", path, delay, exc.kind)
                self._sleep(delay)

    def _get_once(self, path: str, params: dict[str, str] | None) -> Any:
        started = time.monotonic()
        try:
            response = self._client.get(path, params=params)
        except httpx.TimeoutException:
            self._log_failure(path, "timeout", started)
            raise JiraApiError(
                "timeout", "Jira did not answer in time. Check the network or VPN.", True
            ) from None
        except httpx.ConnectError as exc:
            if "CERTIFICATE" in str(exc).upper():
                self._log_failure(path, "tls", started)
                raise JiraApiError(
                    "tls",
                    "The Jira certificate is not trusted by Windows. "
                    "Install the corporate CA or check the VPN.",
                ) from None
            self._log_failure(path, "connection", started)
            raise JiraApiError(
                "connection", "Cannot reach Jira. Check the URL and VPN.", True
            ) from None
        except httpx.TransportError:
            self._log_failure(path, "connection", started)
            raise JiraApiError("connection", "Network error while contacting Jira.", True) from None

        status = response.status_code
        logger.debug("GET %s -> %s in %.0f ms", path, status, (time.monotonic() - started) * 1000)
        if status == 401:
            raise JiraApiError("auth", "Jira rejected the token (401). Store a valid PAT.")
        if status == 403:
            raise JiraApiError("auth", "Jira refused access (403). Check the account permissions.")
        if status == 404:
            raise JiraApiError("not_found", "Not found (404).")
        if status >= 400:
            raise JiraApiError(
                "http", f"Jira answered with HTTP {status}.", status in RETRYABLE_STATUS
            )
        return response.json()

    @staticmethod
    def _log_failure(path: str, kind: str, started: float) -> None:
        elapsed = (time.monotonic() - started) * 1000
        logger.debug("GET %s failed (%s) after %.0f ms", path, kind, elapsed)

    def get_issue(self, key: str) -> dict[str, Any]:
        if not KEY_PATTERN.fullmatch(key):
            raise ValueError(f"Invalid ticket key: {key!r}")
        fields = ",".join(requested_fields(self._settings))
        return self._get(f"/rest/api/2/issue/{quote(key)}", {"fields": fields})

    def get_fields(self) -> list[dict[str, Any]]:
        return self._get("/rest/api/2/field")

    def get_myself(self) -> dict[str, Any]:
        return self._get("/rest/api/2/myself")

    def search(self, jql: str, fields: Sequence[str]) -> Iterator[dict[str, Any]]:
        start = 0
        while True:
            page = self._get(
                "/rest/api/2/search",
                {
                    "jql": jql,
                    "startAt": str(start),
                    "maxResults": str(self._page_size),
                    "fields": ",".join(fields),
                },
            )
            issues = page.get("issues") or []
            if not issues:
                return
            yield from issues
            start += len(issues)
            total = page.get("total")
            if total is None:
                if len(issues) < self._page_size:
                    return
            elif start >= total:
                return


def check_fields(settings: Settings, jira_fields: list[dict[str, Any]]) -> list[FieldFinding]:
    by_id = {field.get("id"): field.get("name") for field in jira_fields}
    ids = settings.fields
    configured = {
        "team": ids.team,
        "simulation_type": ids.simulation_type,
        "target_start": ids.target_start,
        "target_end": ids.target_end,
        "sprint": ids.sprint,
        "epic_link": ids.epic_link,
        "estimated_effort": ids.estimated_effort,
        "remaining_effort": ids.remaining_effort,
        "request_drivers": ids.request_drivers,
        "dyson_project_list": ids.dyson_project_list,
    }
    findings = []
    for setting, field_id in configured.items():
        if not field_id:
            continue
        if field_id not in by_id:
            findings.append(FieldFinding(setting, field_id, "missing"))
            continue
        name = by_id[field_id]
        hint = FIELD_NAME_HINTS.get(setting)
        status = "ok" if not hint or hint in str(name).lower() else "name_mismatch"
        findings.append(FieldFinding(setting, field_id, status, name))
    return findings
