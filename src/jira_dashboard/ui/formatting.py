from datetime import date, datetime

from jira_dashboard.models import Domain, Ticket, TicketStatus

UNKNOWN = "Unknown"


def format_date(value: date | datetime) -> str:
    return f"{value.day:02d} {value:%b %Y}"


def format_days(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def status_text(ticket: Ticket) -> str:
    if ticket.status is TicketStatus.UNKNOWN:
        return f"{UNKNOWN} ({ticket.raw_status})" if ticket.raw_status else UNKNOWN
    return ticket.status.value.replace("_", " ").title()


def domain_value(ticket: Ticket) -> str | None:
    if ticket.domain is Domain.UNSPECIFIED:
        return None
    return ticket.domain.value.title()
