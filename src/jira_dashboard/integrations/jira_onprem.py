import re
from collections.abc import Sequence

from jira_dashboard.config.settings import Settings
from jira_dashboard.integrations.jira_client import JiraClient
from jira_dashboard.models import Ticket
from jira_dashboard.services.secrets import SecretStore

_NOT_AVAILABLE = "Remote Jira access is not implemented yet (MVP-1)."


class JiraNotConfiguredError(RuntimeError):
    pass


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _field_reference(field_id: str) -> str:
    match = re.fullmatch(r"customfield_(\d+)", field_id)
    return f"cf[{match.group(1)}]" if match else field_id


class JiraOnPremClient(JiraClient):
    def __init__(self, settings: Settings, secret_store: SecretStore | None = None) -> None:
        if settings.jira.is_placeholder:
            raise JiraNotConfiguredError(
                "The Jira base URL is not configured. Set jira.base_url in settings.local.toml "
                "or the JIRA_DASHBOARD_JIRA__BASE_URL environment variable."
            )
        self._settings = settings
        self._secret_store = secret_store

    def build_search_jql(self, *, active_sprints_only: bool = False) -> str:
        jira = self._settings.jira
        team_field = _field_reference(self._settings.fields.team)
        jql = f"project = {_quote(jira.project_key)} AND {team_field} = {_quote(jira.team)}"
        if active_sprints_only:
            jql += " AND sprint in openSprints()"
        return jql

    def get_ticket(self, key: str) -> Ticket:
        raise NotImplementedError(_NOT_AVAILABLE)

    def get_tickets(self, keys: Sequence[str]) -> list[Ticket]:
        raise NotImplementedError(_NOT_AVAILABLE)

    def search_tickets(self, *, active_sprints_only: bool = False) -> list[Ticket]:
        raise NotImplementedError(_NOT_AVAILABLE)
