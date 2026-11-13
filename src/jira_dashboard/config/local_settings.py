"""Validation of the Jira address and a safe update of the local settings file.

Only `jira.base_url` is ever written here; the token never touches a file.
"""

import os
import re
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from jira_dashboard.config.settings import LOCAL_FILE_DEFAULT, LOCAL_FILE_ENV, PLACEHOLDER_HOST

ENV_BASE_URL = "JIRA_DASHBOARD_JIRA__BASE_URL"
_TABLE = re.compile(r"^\s*\[([^\]]+)\]\s*(#.*)?$")
_BASE_URL = re.compile(r"^(\s*)base_url\s*=")


class LocalSettingsError(Exception):
    pass


def local_settings_path() -> Path:
    return Path(os.environ.get(LOCAL_FILE_ENV, LOCAL_FILE_DEFAULT))


def validate_address(text: str) -> tuple[str | None, str | None]:
    """Returns (clean address, None) or (None, reason). Reasons never echo credentials."""
    value = text.strip()
    if not value:
        return None, "Enter the Jira address."
    try:
        parts = urlsplit(value)
        host = parts.hostname
        has_credentials = parts.username is not None or parts.password is not None
        port = parts.port
    except ValueError:
        return None, "This is not a valid web address."
    if parts.scheme.lower() != "https":
        return None, "The address must start with https://."
    if not host:
        return None, "The address needs a host name, for example https://jira.example.com."
    if has_credentials or "@" in parts.netloc:
        return None, "Do not put a user name or password in the address."
    if parts.query or parts.fragment or parts.path not in ("", "/"):
        return None, "Use only the site address, without a path, query or fragment."
    if PLACEHOLDER_HOST in host.lower():
        return None, "This is the placeholder address, not a real Jira."
    netloc = f"{host}:{port}" if port else host
    return f"https://{netloc}", None


def _jira_range(lines: list[str]) -> tuple[int, int] | None:
    """Line range [start, end) of the body of the [jira] table."""
    start = None
    for index, line in enumerate(lines):
        match = _TABLE.match(line)
        if match is None:
            continue
        name = match.group(1).strip()
        if start is not None:
            return start, index
        if name == "jira":
            start = index + 1
    return (start, len(lines)) if start is not None else None


def _updated_text(text: str, address: str) -> str:
    lines = text.splitlines()
    newline = "\r\n" if "\r\n" in text else "\n"
    new_line = f'base_url = "{address}"'
    span = _jira_range(lines)
    if span is None:
        if any(re.match(r"^\s*jira\s*=", line) for line in lines):
            raise LocalSettingsError("The settings file defines jira as an inline table.")
        prefix = [*lines, ""] if lines and lines[-1].strip() else lines
        return newline.join([*prefix, "[jira]", new_line]) + newline
    found = [i for i in range(*span) if _BASE_URL.match(lines[i])]
    if len(found) > 1:
        raise LocalSettingsError("The settings file has base_url more than once.")
    if found:
        indent = _BASE_URL.match(lines[found[0]]).group(1)
        lines[found[0]] = indent + new_line
    else:
        lines.insert(span[0], new_line)
    return newline.join(lines) + newline


def set_base_url(path: Path, address: str) -> None:
    """Writes the address into [jira] base_url, keeping the rest; atomic and verified."""
    clean, reason = validate_address(address)
    if clean is None:
        raise LocalSettingsError(reason or "Invalid address.")
    try:
        original = path.read_text(encoding="utf-8") if path.is_file() else ""
        updated = _updated_text(original, clean)
        parsed = tomllib.loads(updated)
        if parsed.get("jira", {}).get("base_url") != clean:
            raise LocalSettingsError("The settings file could not be updated safely.")
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(updated)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    except tomllib.TOMLDecodeError as exc:
        raise LocalSettingsError(f"The settings file is not valid TOML: {exc}") from exc
    except OSError as exc:
        raise LocalSettingsError(f"The settings file could not be written: {exc}") from exc
