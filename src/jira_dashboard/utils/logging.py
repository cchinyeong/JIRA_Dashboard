import logging
import logging.handlers
from pathlib import Path

from jira_dashboard.config.settings import LoggingSettings
from jira_dashboard.utils.redaction import RedactingFilter, RedactingFormatter

LOG_FILE_NAME = "dashboard.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_MARKER = "_jira_dashboard_handler"


def configure_logging(
    settings: LoggingSettings,
    *,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _MARKER, False):
            root.removeHandler(handler)
            handler.close()

    directory = Path(settings.directory)
    directory.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            directory / LOG_FILE_NAME,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        ),
    ]
    for handler in handlers:
        handler.setFormatter(RedactingFormatter(FORMAT))
        handler.addFilter(RedactingFilter())
        setattr(handler, _MARKER, True)
        root.addHandler(handler)
    root.setLevel(settings.level)
