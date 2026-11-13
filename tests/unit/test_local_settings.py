import os
from pathlib import Path

import pytest

from jira_dashboard.config import local_settings
from jira_dashboard.config.local_settings import (
    LocalSettingsError,
    local_settings_path,
    set_base_url,
    validate_address,
)
from jira_dashboard.config.settings import LOCAL_FILE_ENV


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://jira.example.com", "https://jira.example.com"),
        ("https://jira.example.com/", "https://jira.example.com"),
        ("  https://jira.example.com:8443/ ", "https://jira.example.com:8443"),
        ("HTTPS://Jira.Example.com", "https://jira.example.com"),
    ],
)
def test_valid_addresses(text: str, expected: str) -> None:
    assert validate_address(text) == (expected, None)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "http://jira.example.com",
        "jira.example.com",
        "https://",
        "https://jira.example.com/path",
        "https://jira.example.com/?a=1",
        "https://jira.example.com/#top",
        "https://jira.invalid",
        "https://jira.example.com:notaport",
    ],
)
def test_invalid_addresses(text: str) -> None:
    clean, reason = validate_address(text)
    assert clean is None and reason


def test_credentials_are_rejected_without_echoing_them() -> None:
    clean, reason = validate_address("https://user:hunter2@jira.example.com")
    assert clean is None
    assert "hunter2" not in reason and "user" not in reason.replace("user name", "")
    assert validate_address("https://token@jira.example.com")[0] is None


def test_path_follows_the_loader_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)
    assert local_settings_path() == Path("settings.local.toml")
    monkeypatch.setenv(LOCAL_FILE_ENV, "elsewhere.toml")
    assert local_settings_path() == Path("elsewhere.toml")


def test_missing_file_is_created(tmp_path: Path) -> None:
    path = tmp_path / "settings.local.toml"
    set_base_url(path, "https://jira.example.com/")
    assert path.read_text(encoding="utf-8") == '[jira]\nbase_url = "https://jira.example.com"\n'


def test_only_the_address_line_changes(tmp_path: Path) -> None:
    path = tmp_path / "s.toml"
    original = (
        "# my settings\n"
        "[fields]\n"
        'team = "customfield_1"\n'
        "\n"
        "[jira]\n"
        "# the server\n"
        'base_url = "https://old.example.com"  \n'
        "page_size = 50\n"
        "\n"
        "[logging]\n"
        'level = "DEBUG"\n'
    )
    path.write_text(original, encoding="utf-8")
    set_base_url(path, "https://new.example.com")
    assert path.read_text(encoding="utf-8") == original.replace(
        'base_url = "https://old.example.com"  ', 'base_url = "https://new.example.com"'
    )


def test_address_line_added_to_existing_jira_table(tmp_path: Path) -> None:
    path = tmp_path / "s.toml"
    path.write_text("[jira]\npage_size = 50\n[logging]\nlevel = 'INFO'\n", encoding="utf-8")
    set_base_url(path, "https://jira.example.com")
    text = path.read_text(encoding="utf-8")
    assert 'base_url = "https://jira.example.com"' in text
    assert "page_size = 50" in text and "level = 'INFO'" in text


def test_jira_table_appended_to_a_file_without_one(tmp_path: Path) -> None:
    path = tmp_path / "s.toml"
    path.write_text("[logging]\nlevel = 'INFO'", encoding="utf-8")
    set_base_url(path, "https://jira.example.com")
    assert path.read_text(encoding="utf-8").endswith(
        "level = 'INFO'\n\n[jira]\nbase_url = \"https://jira.example.com\"\n"
    )


@pytest.mark.parametrize(
    "content",
    [
        'jira = { base_url = "https://old.example.com" }\n',
        '[jira]\nbase_url = "https://a.example.com"\nbase_url = "https://b.example.com"\n',
        "[jira\nbroken",
    ],
)
def test_unusual_files_are_rejected_and_left_untouched(tmp_path: Path, content: str) -> None:
    path = tmp_path / "s.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LocalSettingsError):
        set_base_url(path, "https://jira.example.com")
    assert path.read_text(encoding="utf-8") == content
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_address_is_not_written(tmp_path: Path) -> None:
    path = tmp_path / "s.toml"
    with pytest.raises(LocalSettingsError):
        set_base_url(path, "http://jira.example.com")
    assert not path.exists()


def test_failed_write_keeps_the_old_file_and_leaves_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "s.toml"
    path.write_text('[jira]\nbase_url = "https://old.example.com"\n', encoding="utf-8")

    def boom(*_args, **_kwargs) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(LocalSettingsError, match="could not be written"):
        set_base_url(path, "https://new.example.com")
    assert "old.example.com" in path.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [path]
    assert local_settings.os is os


def test_written_file_is_read_by_the_settings_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from jira_dashboard.config import get_settings

    path = tmp_path / "s.toml"
    monkeypatch.setenv(LOCAL_FILE_ENV, str(path))
    monkeypatch.delenv("JIRA_DASHBOARD_JIRA__BASE_URL", raising=False)
    set_base_url(local_settings_path(), "https://jira.example.com")
    assert get_settings().jira.base_url == "https://jira.example.com"
