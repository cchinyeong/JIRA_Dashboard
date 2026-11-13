from enum import StrEnum


def _normalise(text: str) -> str:
    return "_".join(text.strip().upper().split())


class TicketStatus(StrEnum):
    NEW = "NEW"
    REFINEMENT = "REFINEMENT"
    BACKLOG = "BACKLOG"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"

    @classmethod
    def from_jira(cls, name: str) -> TicketStatus:
        try:
            return cls(_normalise(name))
        except ValueError:
            raise ValueError(f"Unsupported Jira status: {name!r}") from None


class TicketKind(StrEnum):
    REQUEST = "REQUEST"
    TASK = "TASK"
    OTHER = "OTHER"


class UserRole(StrEnum):
    PROJECT_LEAD = "PROJECT_LEAD"
    DOMAIN_LEAD = "DOMAIN_LEAD"
    DOMAIN_ENGINEER = "DOMAIN_ENGINEER"


class Domain(StrEnum):
    STATIC = "STATIC"
    DYNAMIC = "DYNAMIC"
    OPTICS = "OPTICS"
    THERMAL = "THERMAL"
    MOLDFLOW = "MOLDFLOW"
    CFD = "CFD"
    ACOUSTIC = "ACOUSTIC"
    MULTIPHYSICS = "MULTIPHYSICS"
    OTHER = "OTHER"
    UNSPECIFIED = "UNSPECIFIED"

    @classmethod
    def from_simulation_type(cls, text: str | None) -> Domain:
        if text is None:
            return cls.UNSPECIFIED
        key = _normalise(text)
        if key in ("", "NONE"):
            return cls.UNSPECIFIED
        try:
            return cls(key)
        except ValueError:
            return cls.OTHER
