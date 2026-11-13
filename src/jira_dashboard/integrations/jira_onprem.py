import re
import time
from collections.abc import Callable, Iterable, Sequence

import httpx

from jira_dashboard.config.settings import Settings
from jira_dashboard.integrations.jira_client import JiraClient, TicketBatch, TicketFailure
from jira_dashboard.integrations.jira_http import (
    KEY_PATTERN,
    JiraApiError,
    JiraHttp,
    requested_fields,
)
from jira_dashboard.integrations.jira_mapping import TicketMappingError, map_issue
from jira_dashboard.models import Ticket, TicketStatus
from jira_dashboard.services.secrets import JIRA_PAT, SecretStore, get_secret

CHUNK_SIZE = 50


class JiraNotConfiguredError(RuntimeError):
    pass


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _field_reference(field_id: str) -> str:
    match = re.fullmatch(r"customfield_(\d+)", field_id)
    return f"cf[{match.group(1)}]" if match else field_id


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


class JiraOnPremClient(JiraClient):
    def __init__(
        self,
        settings: Settings,
        secret_store: SecretStore | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if settings.jira.is_placeholder:
            raise JiraNotConfiguredError(
                "The Jira base URL is not configured. Set jira.base_url in settings.local.toml "
                "or the JIRA_DASHBOARD_JIRA__BASE_URL environment variable."
            )
        self._settings = settings
        self._secret_store = secret_store
        self._transport = transport
        self._sleep = sleep
        self._http: JiraHttp | None = None

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def _client(self) -> JiraHttp:
        if self._http is None:
            token = get_secret(JIRA_PAT, self._secret_store)
            self._http = JiraHttp(
                self._settings, token, transport=self._transport, sleep=self._sleep
            )
        return self._http

    def build_search_jql(self, *, in_sprints_only: bool = False) -> str:
        jira = self._settings.jira
        team_field = _field_reference(self._settings.fields.team)
        closed = TicketStatus.CLOSED.value.title()
        jql = f"project = {_quote(jira.project_key)} AND {team_field} = {jira.team_id}"
        excluded = self._settings.issues.excluded_types
        if excluded:
            jql += f" AND issuetype not in ({', '.join(_quote(t) for t in excluded)})"
        if in_sprints_only:
            jql += " AND sprint in (openSprints(), futureSprints())"
        jql += f" AND (status != {_quote(closed)} OR updated >= -{jira.closed_lookback_days}d)"
        return jql + " ORDER BY key ASC"

    def get_ticket(self, key: str) -> Ticket:
        try:
            raw = self._client().get_issue(key)
        except JiraApiError as exc:
            if exc.kind == "not_found":
                raise JiraApiError(
                    "not_found", f"Ticket {key} was not found, or you cannot see it."
                ) from None
            raise
        return map_issue(raw, self._settings)

    def get_tickets(self, keys: Sequence[str]) -> TicketBatch:
        unique = list(dict.fromkeys(keys))
        for key in unique:
            if not KEY_PATTERN.fullmatch(key):
                raise ValueError(f"Invalid ticket key: {key!r}")
        batch = TicketBatch()
        for chunk in _chunks(unique, CHUNK_SIZE):
            jql = f"key in ({', '.join(chunk)}) ORDER BY key ASC"
            self._collect(jql, batch)
        return batch

    def search_tickets(self, *, in_sprints_only: bool = False) -> TicketBatch:
        batch = TicketBatch()
        self._collect(self.build_search_jql(in_sprints_only=in_sprints_only), batch)
        return batch

    def _collect(self, jql: str, batch: TicketBatch) -> None:
        for raw in self._client().search(jql, requested_fields(self._settings)):
            try:
                batch.tickets.append(map_issue(raw, self._settings))
            except TicketMappingError as exc:
                batch.failures.append(TicketFailure(exc.key, exc.reason))
