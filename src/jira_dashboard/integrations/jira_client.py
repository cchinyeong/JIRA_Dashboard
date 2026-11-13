from abc import ABC, abstractmethod
from collections.abc import Sequence

from jira_dashboard.models import Ticket


class JiraClient(ABC):
    @abstractmethod
    def get_ticket(self, key: str) -> Ticket: ...

    @abstractmethod
    def get_tickets(self, keys: Sequence[str]) -> list[Ticket]: ...

    @abstractmethod
    def search_tickets(self, *, active_sprints_only: bool = False) -> list[Ticket]: ...
