import logging

import pytest

from jira_dashboard.config.settings import LoggingSettings
from jira_dashboard.utils.logging import LOG_FILE_NAME, configure_logging
from jira_dashboard.utils.redaction import clear_secrets, redact, register_secret


@pytest.fixture(autouse=True)
def _clean():
    clear_secrets()
    yield
    clear_secrets()
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_jira_dashboard_handler", False):
            root.removeHandler(handler)
            handler.close()


def settings(tmp_path, level: str = "INFO") -> LoggingSettings:
    return LoggingSettings(level=level, directory=str(tmp_path / "logs"))


@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Bearer abc12345",
        "header Authorization=Basic abc12345",
        "sent Bearer abc12345 now",
        "token=abc12345",
        'password: "abc12345"',
        "api_key=abc12345",
    ],
)
def test_pattern_redaction(text: str) -> None:
    assert "abc12345" not in redact(text)


def test_ordinary_text_untouched() -> None:
    assert redact("Fetched 12 tickets") == "Fetched 12 tickets"


def test_registered_value_masked_and_short_ignored() -> None:
    register_secret("s3cr3t-value")
    register_secret("ab")
    assert redact("value s3cr3t-value, ab") == "value ***, ab"


def test_file_created_and_level_applied(tmp_path) -> None:
    configure_logging(settings(tmp_path, "DEBUG"))
    logging.getLogger("t").debug("hello debug")
    text = (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "hello debug" in text


def test_info_level_hides_debug(tmp_path) -> None:
    configure_logging(settings(tmp_path))
    logging.getLogger("t").debug("hidden")
    logging.getLogger("t").info("shown")
    text = (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "shown" in text
    assert "hidden" not in text


def test_setup_is_idempotent(tmp_path) -> None:
    configure_logging(settings(tmp_path))
    configure_logging(settings(tmp_path))
    logging.getLogger("t").info("once")
    text = (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert text.count("once") == 1


def test_rotation_is_bounded(tmp_path) -> None:
    configure_logging(settings(tmp_path), max_bytes=200, backup_count=2)
    for i in range(100):
        logging.getLogger("t").info("line %d %s", i, "x" * 40)
    files = list((tmp_path / "logs").glob("dashboard.log*"))
    assert 1 < len(files) <= 3


def test_secret_in_args_and_traceback_masked(tmp_path) -> None:
    register_secret("pat-9876-secret")
    configure_logging(settings(tmp_path))
    log = logging.getLogger("t")
    log.info("using %s", "pat-9876-secret")
    try:
        raise RuntimeError("failed with pat-9876-secret")
    except RuntimeError:
        log.exception("boom")
    text = (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "pat-9876-secret" not in text
    assert "boom" in text
