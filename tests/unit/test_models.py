from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from jira_dashboard.models import (
    Domain,
    Project,
    Sprint,
    Ticket,
    TicketKind,
    TicketStatus,
    User,
    UserRole,
)


def make_ticket(**kwargs) -> Ticket:
    defaults = {
        "jira_key": "CAE-1558",
        "summary": "Wand Assy robustness",
        "project": Project("VE_CAE", "VE CAE"),
        "status": TicketStatus.IN_PROGRESS,
    }
    return Ticket(**(defaults | kwargs))


@pytest.mark.parametrize("name", ["NEW", "Refinement", "in progress", " Closed "])
def test_status_from_jira(name: str) -> None:
    assert TicketStatus.from_jira(name) in TicketStatus


def test_status_in_progress_with_space() -> None:
    assert TicketStatus.from_jira("In Progress") is TicketStatus.IN_PROGRESS


def test_status_rejects_implemented() -> None:
    with pytest.raises(ValueError):
        TicketStatus.from_jira("IMPLEMENTED")


def test_status_and_role_membership() -> None:
    assert len(TicketStatus) == 6
    assert {r.name for r in UserRole} == {"PROJECT_LEAD", "DOMAIN_LEAD", "DOMAIN_ENGINEER"}


@pytest.mark.parametrize("text", [None, "", "None", "  none "])
def test_domain_unspecified(text: str | None) -> None:
    assert Domain.from_simulation_type(text) is Domain.UNSPECIFIED


def test_domain_known_and_unknown() -> None:
    assert Domain.from_simulation_type("Moldflow") is Domain.MOLDFLOW
    assert Domain.from_simulation_type("Static") is Domain.STATIC
    assert Domain.from_simulation_type("Fatigue") is Domain.OTHER


def test_minimal_ticket_defaults() -> None:
    ticket = make_ticket()
    assert ticket.requester is None
    assert ticket.assignee is None
    assert ticket.request_drivers == ()
    assert ticket.domain is Domain.UNSPECIFIED


def test_ticket_full_fields() -> None:
    ticket = make_ticket(
        request_drivers=("Risk", "Verification"),
        estimated_effort=4,
        requester="Mohamad Faizal",
        assignee=User("cchong", "CY Chong"),
        sprint=Sprint(1, "Static Sprint", "ACTIVE", end_date=date(2026, 11, 16)),
        target_end_date=date(2026, 11, 11),
    )
    assert ticket.request_drivers == ("Risk", "Verification")
    assert ticket.estimated_effort == 4.0
    assert ticket.sprint.end_date == date(2026, 11, 16)


@pytest.mark.parametrize(
    ("status", "blocked"),
    [
        (TicketStatus.REFINEMENT, True),
        (TicketStatus.BACKLOG, False),
        (TicketStatus.PLANNED, False),
        (TicketStatus.IN_PROGRESS, False),
    ],
)
def test_is_blocked_only_for_refinement(status: TicketStatus, blocked: bool) -> None:
    assert make_ticket(status=status).is_blocked is blocked


def test_models_are_immutable() -> None:
    ticket = make_ticket()
    with pytest.raises(FrozenInstanceError):
        ticket.summary = "changed"
    assert ticket.summary == "Wand Assy robustness"
    with pytest.raises(FrozenInstanceError):
        Project("A", "B").name = "C"


def test_ticket_kinds_and_defaults() -> None:
    assert {k.name for k in TicketKind} == {"REQUEST", "TASK", "OTHER"}
    assert make_ticket().kind is TicketKind.OTHER


def test_parent_key() -> None:
    task = make_ticket(kind=TicketKind.TASK, parent_key="CAE-1513")
    assert task.parent_key == "CAE-1513"
    assert make_ticket(kind=TicketKind.REQUEST).parent_key is None
