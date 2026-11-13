import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from jira_dashboard.config.settings import Settings
from jira_dashboard.integrations.jira_client import JiraClient
from jira_dashboard.integrations.jira_http import JiraApiError
from jira_dashboard.models import Ticket
from jira_dashboard.services.secrets import MissingSecretError
from jira_dashboard.services.ticket_query import (
    FacetValue,
    GroupedView,
    Snapshot,
    Summary,
    TicketFilter,
    facets,
    filter_tickets,
    group,
    make_snapshot,
    summarise,
)

logger = logging.getLogger(__name__)

MAX_PARENT_ROUNDS = 3
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_BUSY = "busy"


@dataclass(frozen=True, slots=True)
class RefreshResult:
    status: str
    error_kind: str | None = None
    message: str | None = None
    warnings: tuple[str, ...] = ()
    ticket_count: int = 0
    parent_count: int = 0
    failure_count: int = 0

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def _now() -> datetime:
    return datetime.now(UTC)


class TicketService:
    """Refreshes ticket data from a JiraClient and answers the UI's questions about it."""

    def __init__(
        self,
        client: JiraClient,
        settings: Settings,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._client = client
        self._settings = settings
        self._clock = clock
        self._snapshot = make_snapshot(())
        self._lock = threading.Lock()

    @property
    def snapshot(self) -> Snapshot:
        return self._snapshot

    def refresh(self, *, in_sprints_only: bool = False) -> RefreshResult:
        if not self._lock.acquire(blocking=False):
            return RefreshResult(STATUS_BUSY, message="A refresh is already running.")
        try:
            return self._refresh(in_sprints_only)
        finally:
            self._lock.release()

    def _refresh(self, in_sprints_only: bool) -> RefreshResult:
        try:
            batch = self._client.search_tickets(in_sprints_only=in_sprints_only)
        except JiraApiError as exc:
            return self._failed(exc.kind, str(exc))
        except MissingSecretError as exc:
            return self._failed("no_token", str(exc))
        except Exception:
            logger.exception("Unexpected error while refreshing tickets")
            return self._failed(
                "unexpected", "Unexpected error while refreshing. See the log for details."
            )

        tickets = {ticket.jira_key: ticket for ticket in batch.tickets}
        failures = list(batch.failures)
        context, warnings = self._load_parents(tickets, failures)

        snapshot = make_snapshot(
            tickets.values(), context.values(), failures, warnings, self._clock()
        )
        self._snapshot = snapshot
        return RefreshResult(
            STATUS_OK,
            warnings=tuple(warnings),
            ticket_count=len(snapshot.tickets),
            parent_count=len(snapshot.context),
            failure_count=len(failures),
        )

    def _missing_parents(self, known: set[str], gathered: Sequence[Ticket]) -> list[str]:
        wanted = {t.parent_key for t in gathered if t.parent_key and t.parent_key not in known}
        return sorted(wanted)

    def _load_parents(
        self, tickets: dict[str, Ticket], failures: list
    ) -> tuple[dict[str, Ticket], list[str]]:
        context: dict[str, Ticket] = {}
        warnings: list[str] = []
        asked = set(tickets)
        for _ in range(MAX_PARENT_ROUNDS):
            missing = self._missing_parents(asked, [*tickets.values(), *context.values()])
            if not missing:
                return context, warnings
            asked.update(missing)
            try:
                batch = self._client.get_tickets(missing)
            except (JiraApiError, MissingSecretError) as exc:
                warnings.append(f"Parent tickets could not be loaded: {exc}")
                return context, warnings
            except Exception:
                logger.exception("Unexpected error while loading parent tickets")
                warnings.append("Parent tickets could not be loaded (unexpected error).")
                return context, warnings
            for ticket in batch.tickets:
                context[ticket.jira_key] = ticket
            failures.extend(batch.failures)
        if self._missing_parents(asked, [*tickets.values(), *context.values()]):
            warnings.append(
                f"The hierarchy is deeper than {MAX_PARENT_ROUNDS} levels; higher parents "
                "were not loaded."
            )
        return context, warnings

    @staticmethod
    def _failed(kind: str, message: str) -> RefreshResult:
        logger.warning("Refresh failed (%s): %s", kind, message)
        return RefreshResult(STATUS_FAILED, error_kind=kind, message=message)

    def list_tickets(self, criteria: TicketFilter | None = None) -> list[Ticket]:
        return filter_tickets(self._snapshot.tickets, criteria)

    def facets(self) -> dict[str, list[FacetValue]]:
        return facets(self._snapshot.tickets)

    def grouped(self, tickets: Sequence[Ticket] | None = None) -> GroupedView:
        snapshot = self._snapshot
        return group(snapshot.tickets if tickets is None else tickets, snapshot)

    def summary(self) -> Summary:
        return summarise(self._snapshot)

    def ticket_link(self, ticket: Ticket) -> str | None:
        url = ticket.jira_url
        base = self._settings.jira.base_url
        if not url or not url.startswith(base + "/"):
            return None
        if urlparse(url).hostname != urlparse(base).hostname:
            return None
        return url
