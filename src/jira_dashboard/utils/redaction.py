import logging
import re
import threading

MASK = "***"
MIN_SECRET_LENGTH = 4

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)(?:(?:bearer|basic)\s+)?[^\s'\",]+"),
        r"\1" + MASK,
    ),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"), r"\1 " + MASK),
    (
        re.compile(r"(?i)\b(token|password|secret|api_?key)(['\"]?\s*[=:]\s*['\"]?)[^\s'\",&]+"),
        r"\1\2" + MASK,
    ),
]

_secrets: set[str] = set()
_lock = threading.Lock()


def register_secret(value: str) -> None:
    if len(value) >= MIN_SECRET_LENGTH:
        with _lock:
            _secrets.add(value)


def clear_secrets() -> None:
    with _lock:
        _secrets.clear()


def redact(text: str) -> str:
    with _lock:
        known = sorted(_secrets, key=len, reverse=True)
    for secret in known:
        text = text.replace(secret, MASK)
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))
