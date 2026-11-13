import pytest
from pydantic import ValidationError

from jira_dashboard.config import Settings, get_settings
from jira_dashboard.config.settings import LOCAL_FILE_ENV
from jira_dashboard.models import TicketStatus


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(LOCAL_FILE_ENV, raising=False)


def write_local(tmp_path, text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "override.toml"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setenv(LOCAL_FILE_ENV, str(path))


def test_defaults() -> None:
    s = get_settings()
    assert s.jira.project_key == "CAE"
    assert s.jira.team == "Structural Analysis"
    assert s.fields.target_start == "customfield_12112"
    assert s.fields.target_end == "customfield_12113"
    assert s.fields.sprint == "customfield_10000"
    assert s.fields.team == "customfield_12110"
    assert s.fields.simulation_type == "customfield_15253"
    assert s.fields.actual_start is None
    assert (s.working_time.hours_per_day, s.working_time.days_per_week) == (8, 5)
    assert s.requester.panel_title == "PIC (Requester - Full Name)"
    assert "Requester" in s.requester.placeholders


def test_board_maps_differ() -> None:
    boards = get_settings().boards
    assert boards.project_lead[TicketStatus.BACKLOG] == "Backlog"
    assert boards.active_sprint[TicketStatus.BACKLOG] == "On Hold"
    assert boards.project_lead[TicketStatus.REFINEMENT] == "On Hold"
    assert TicketStatus.REFINEMENT not in boards.active_sprint


def test_placeholder_url(tmp_path, monkeypatch) -> None:
    assert get_settings().jira.is_placeholder
    write_local(tmp_path, '[jira]\nbase_url = "https://jira.example.com/"\n', monkeypatch)
    s = get_settings()
    assert s.jira.base_url == "https://jira.example.com"
    assert not s.jira.is_placeholder
    assert s.jira.project_key == "CAE"


def test_env_beats_file(tmp_path, monkeypatch) -> None:
    write_local(tmp_path, '[jira]\nbase_url = "https://file.example.com"\n', monkeypatch)
    monkeypatch.setenv("JIRA_DASHBOARD_JIRA__BASE_URL", "https://env.example.com")
    assert get_settings().jira.base_url == "https://env.example.com"


def test_rejects_http_url(tmp_path, monkeypatch) -> None:
    write_local(tmp_path, '[jira]\nbase_url = "http://jira.example.com"\n', monkeypatch)
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.parametrize(
    "text",
    ["[working_time]\nhours_per_day = 0\n", '[logging]\nlevel = "LOUD"\n'],
)
def test_rejects_invalid_values(text, tmp_path, monkeypatch) -> None:
    write_local(tmp_path, text, monkeypatch)
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.parametrize("key", ["token", "password"])
def test_rejects_credential_keys(key, tmp_path, monkeypatch) -> None:
    write_local(tmp_path, f'[jira]\n{key} = "x"\n', monkeypatch)
    with pytest.raises(ValidationError, match=key):
        get_settings()


def test_unknown_top_level_key(tmp_path, monkeypatch) -> None:
    write_local(tmp_path, 'secret = "x"\n', monkeypatch)
    with pytest.raises(ValidationError, match="secret"):
        get_settings()


def test_settings_immutable() -> None:
    s: Settings = get_settings()
    with pytest.raises(ValidationError):
        s.jira = s.jira
    with pytest.raises(ValidationError):
        s.jira.project_key = "X"


def test_retrieval_defaults() -> None:
    jira = get_settings().jira
    assert (jira.page_size, jira.max_retries, jira.closed_lookback_days) == (100, 2, 30)


def test_team_defaults() -> None:
    jira = get_settings().jira
    assert (jira.team, jira.team_id) == ("Structural Analysis", 400)


@pytest.mark.parametrize("value", [0, -5])
def test_team_id_must_be_positive(value, tmp_path, monkeypatch) -> None:
    write_local(tmp_path, f"[jira]\nteam_id = {value}\n", monkeypatch)
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.parametrize(
    "line",
    ["page_size = 0", "page_size = 5000", "max_retries = -1", "closed_lookback_days = -1"],
)
def test_retrieval_settings_validated(line, tmp_path, monkeypatch) -> None:
    write_local(tmp_path, f"[jira]\n{line}\n", monkeypatch)
    with pytest.raises(ValidationError):
        get_settings()


def test_retrieval_boundaries_accepted(tmp_path, monkeypatch) -> None:
    text = "[jira]\npage_size = 1000\nmax_retries = 0\nclosed_lookback_days = 0\n"
    write_local(tmp_path, text, monkeypatch)
    jira = get_settings().jira
    assert (jira.page_size, jira.max_retries, jira.closed_lookback_days) == (1000, 0, 0)


def test_issue_hierarchy_defaults() -> None:
    s = get_settings()
    assert s.issues.request_types == ("Epic", "Risk", "Issue")
    assert s.issues.task_types == ("Task",)
    assert s.issues.epic_type == "Epic"
    assert s.issues.task_parent_phrases == ("is child of",)
    assert s.issues.request_parent_phrases == ("is caused by",)
    assert s.fields.epic_link == "customfield_10001"


def test_data_quality_defaults() -> None:
    issues = get_settings().issues
    assert issues.excluded_types == ("Sub-task",)
    assert issues.request_wrong_epic_phrases == ("is child of", "created by")
    wrong = {p.lower() for p in issues.request_wrong_epic_phrases}
    assert not wrong & {p.lower() for p in issues.request_parent_phrases}


def test_mentions_is_not_a_parent_phrase() -> None:
    issues = get_settings().issues
    phrases = {p.lower() for p in (*issues.task_parent_phrases, *issues.request_parent_phrases)}
    assert not phrases & {"mentions", "is mentioned by"}


def test_old_combined_phrase_key_rejected(tmp_path, monkeypatch) -> None:
    write_local(tmp_path, '[issues]\nparent_link_phrases = ["is child of"]\n', monkeypatch)
    with pytest.raises(ValidationError, match="parent_link_phrases"):
        get_settings()


def test_documented_override_loads(tmp_path, monkeypatch) -> None:
    write_local(
        tmp_path,
        '[issues]\ntask_parent_phrases = ["is child of", "is part of"]\n',
        monkeypatch,
    )
    assert get_settings().issues.task_parent_phrases == ("is child of", "is part of")


def test_overlapping_issue_types_rejected(tmp_path, monkeypatch) -> None:
    write_local(tmp_path, '[issues]\ntask_types = ["Task", "risk"]\n', monkeypatch)
    with pytest.raises(ValidationError, match="risk"):
        get_settings()
