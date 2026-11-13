from datetime import UTC, date, datetime

from jira_dashboard.models import Domain, Project, Sprint, Ticket, TicketStatus, User

PROJECT = Project(key="CAE", name="CAE")


def make_ticket(key: str = "CAE-1", **overrides) -> Ticket:
    fields = {
        "jira_key": key,
        "summary": "Summary",
        "project": PROJECT,
        "status": TicketStatus.IN_PROGRESS,
        "issue_type": "Task",
        "priority": "High",
        "domain": Domain.CFD,
        "assignee": User(username="ann", display_name="Ann"),
        "sprint": Sprint(id=1, name="Sprint 1", state="ACTIVE"),
        "target_end_date": date(2026, 11, 5),
        "remaining_effort": 2.5,
        "updated_date": datetime(2026, 11, 1, tzinfo=UTC),
    }
    fields.update(overrides)
    return Ticket(**fields)
