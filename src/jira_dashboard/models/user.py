from dataclasses import dataclass

from jira_dashboard.models.enums import UserRole


@dataclass(frozen=True, slots=True)
class User:
    username: str
    display_name: str
    email: str | None = None
    role: UserRole | None = None
