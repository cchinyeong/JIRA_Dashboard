import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from jira_dashboard.config.settings import Settings

REQUESTER_PLACEHOLDER = "Person A."
REDACTED = "<redacted>"
SAFE_EMAIL_DOMAIN = "@example.com"

_PANEL = re.compile(r"\{panel(?::([^}]*))?\}(.*?)\{panel\}", re.DOTALL)
_PANEL_TITLE = re.compile(r"title=([^|]*)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_SPRINT_KEYS = ("id", "name", "state", "startDate", "endDate")
_LINK_TYPE_KEYS = ("name", "inward", "outward")
_EPIC_KEYS = ("key", "id", "name", "value")


class UserAliases:
    """Replaces people by consistent synthetic users."""

    def __init__(self) -> None:
        self._numbers: dict[str, int] = {}

    def alias(self, user: Mapping[str, Any] | None) -> dict[str, str] | None:
        if not user:
            return None
        identity = (
            user.get("name")
            or user.get("key")
            or user.get("emailAddress")
            or user.get("displayName")
        )
        if not identity:
            return None
        number = self._numbers.setdefault(identity, len(self._numbers) + 1)
        return {
            "name": f"user-{number}",
            "displayName": f"User {number}",
            "emailAddress": f"user-{number}@example.com",
        }


def sanitize_description(description: str | None, requester_title: str) -> str | None:
    if not description:
        return None
    panels = []
    for params, _body in _PANEL.findall(description):
        match = _PANEL_TITLE.search(params or "")
        title = match.group(1).strip() if match else ""
        body = REQUESTER_PLACEHOLDER if title.lower() == requester_title.lower() else REDACTED
        panels.append(f"{{panel:title={title}}}\n{body}\n{{panel}}")
    return "\n".join(panels) if panels else REDACTED


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _name_only(value: Any) -> dict[str, Any] | None:
    return {"name": value.get("name")} if isinstance(value, Mapping) else None


def _sprint_item(item: Any) -> Any:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        return {key: item.get(key) for key in _SPRINT_KEYS if key in item}
    return None


def _sprints(value: Any) -> list[Any] | None:
    if value is None:
        return None
    items = value if isinstance(value, list) else [value]
    return [_sprint_item(item) for item in items]


def _epic_link(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return {key: value[key] for key in _EPIC_KEYS if isinstance(value.get(key), str)}
    return None


def _number(value: Any) -> int | float | None:
    return value if isinstance(value, int | float) and not isinstance(value, bool) else None


def _link(link: Mapping[str, Any]) -> dict[str, Any]:
    link_type = link.get("type") or {}
    result: dict[str, Any] = {"type": {key: link_type.get(key) for key in _LINK_TYPE_KEYS}}
    for side in ("inwardIssue", "outwardIssue"):
        other = link.get(side)
        if other:
            other_type = ((other.get("fields") or {}).get("issuetype") or {}).get("name")
            result[side] = {"key": other.get("key"), "fields": {"issuetype": {"name": other_type}}}
    return result


def sanitize_issue(
    payload: Mapping[str, Any], settings: Settings, users: UserAliases
) -> dict[str, Any]:
    key = payload["key"]
    source = payload.get("fields") or {}
    ids = settings.fields
    project = source.get("project") or {}

    simulation = source.get(ids.simulation_type)
    if isinstance(simulation, Mapping):
        simulation = {"value": simulation.get("value")}
    else:
        simulation = _text(simulation)

    fields: dict[str, Any] = {
        "summary": f"Sample ticket {key}",
        "description": sanitize_description(
            source.get("description"), settings.requester.panel_title
        ),
        "project": {"key": project.get("key"), "name": project.get("name")},
        "issuetype": _name_only(source.get("issuetype")),
        "priority": _name_only(source.get("priority")),
        "status": _name_only(source.get("status")),
        ids.request_drivers: [
            {"name": item.get("name")} for item in source.get(ids.request_drivers) or []
        ],
        ids.simulation_type: simulation,
        ids.target_start: _text(source.get(ids.target_start)),
        ids.target_end: _text(source.get(ids.target_end)),
        ids.sprint: _sprints(source.get(ids.sprint)),
        ids.estimated_effort: _number(source.get(ids.estimated_effort)),
        ids.remaining_effort: _number(source.get(ids.remaining_effort)),
        "assignee": users.alias(source.get("assignee")),
        "reporter": users.alias(source.get("reporter")),
        "created": _text(source.get("created")),
        "updated": _text(source.get("updated")),
        "issuelinks": [_link(link) for link in source.get("issuelinks") or []],
    }
    if ids.epic_link:
        fields[ids.epic_link] = _epic_link(source.get(ids.epic_link))
    return {"key": key, "fields": fields}


def find_leaks(text: str, base_url: str, token: str | None = None) -> list[str]:
    leaks = []
    host = urlparse(base_url).hostname
    if host and host.lower() in text.lower():
        leaks.append("Jira host name")
    if any(not match.lower().endswith(SAFE_EMAIL_DOMAIN) for match in _EMAIL.findall(text)):
        leaks.append("e-mail address")
    if token and len(token) >= 4 and token in text:
        leaks.append("token")
    return leaks
