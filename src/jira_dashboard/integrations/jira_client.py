from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from jira_dashboard.models import Ticket


@dataclass(frozen=True, slots=True)
class TicketFailure:
    key: str
    reason: str


@dataclass(frozen=True, slots=True)
class TicketBatch:
    tickets: list[Ticket] = field(default_factory=list)
    failures: list[TicketFailure] = field(default_factory=list)


class JiraClient(ABC):
    @abstractmethod
    def get_ticket(self, key: str) -> Ticket: ...

    @abstractmethod
    def get_tickets(self, keys: Sequence[str]) -> TicketBatch: ...

    @abstractmethod
    def search_tickets(self, *, in_sprints_only: bool = False) -> TicketBatch: ...
