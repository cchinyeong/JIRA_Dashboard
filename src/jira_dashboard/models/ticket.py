from dataclasses import dataclass
from datetime import date, datetime

from jira_dashboard.models.enums import Domain, TicketKind, TicketStatus
from jira_dashboard.models.project import Project
from jira_dashboard.models.sprint import Sprint
from jira_dashboard.models.user import User


@dataclass(frozen=True, slots=True)
class Ticket:
    jira_key: str
    summary: str
    project: Project
    status: TicketStatus
    description: str | None = None
    issue_type: str | None = None
    domain: Domain = Domain.UNSPECIFIED
    request_drivers: tuple[str, ...] = ()
    assignee: User | None = None
    reporter: User | None = None
    requester: str | None = None
    priority: str | None = None
    target_start_date: date | None = None
    target_end_date: date | None = None
    actual_start_date: date | None = None
    completion_date: date | None = None
    created_date: datetime | None = None
    updated_date: datetime | None = None
    sprint: Sprint | None = None
    estimated_effort: float | None = None
    remaining_effort: float | None = None
    blocked_reason: str | None = None
    jira_url: str | None = None
    kind: TicketKind = TicketKind.OTHER
    parent_key: str | None = None

    @property
    def is_blocked(self) -> bool:
        return self.status is TicketStatus.REFINEMENT
