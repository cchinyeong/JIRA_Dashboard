import os
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from jira_dashboard.models import TicketStatus

PLACEHOLDER_HOST = "jira.invalid"
DEFAULT_TOML = Path(__file__).with_name("default.toml")
LOCAL_FILE_ENV = "JIRA_DASHBOARD_CONFIG_FILE"
LOCAL_FILE_DEFAULT = "settings.local.toml"
LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


def _field_id(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError(f"invalid Jira field id: {value!r}")
    return value


FieldId = Annotated[str, AfterValidator(_field_id)]


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class JiraSettings(_Section):
    base_url: str
    project_key: str
    team: str
    timeout_seconds: int = Field(gt=0)

    @field_validator("base_url")
    @classmethod
    def _https_only(cls, value: str) -> str:
        if not value.lower().startswith("https://") or len(value) <= len("https://"):
            raise ValueError("Jira base URL must use HTTPS")
        return value.rstrip("/")

    @property
    def is_placeholder(self) -> bool:
        return PLACEHOLDER_HOST in self.base_url


class FieldMapping(_Section):
    team: FieldId
    simulation_type: FieldId
    target_start: FieldId
    target_end: FieldId
    sprint: FieldId
    estimated_effort: FieldId
    remaining_effort: FieldId
    request_drivers: FieldId
    epic_link: FieldId | None = None
    actual_start: FieldId | None = None


class WorkingTime(_Section):
    hours_per_day: float = Field(gt=0)
    days_per_week: float = Field(gt=0)


class RequesterTemplate(_Section):
    panel_title: str
    placeholders: tuple[str, ...]


class IssueSettings(_Section):
    request_types: tuple[str, ...]
    task_types: tuple[str, ...]
    parent_link_phrases: tuple[str, ...]

    @model_validator(mode="after")
    def _no_overlap(self) -> IssueSettings:
        overlap = {t.lower() for t in self.request_types} & {t.lower() for t in self.task_types}
        if overlap:
            raise ValueError(
                f"issue type {sorted(overlap)[0]!r} is configured as both request and task"
            )
        return self


class BoardMaps(_Section):
    project_lead: dict[TicketStatus, str]
    active_sprint: dict[TicketStatus, str]


class RiskThresholds(_Section):
    amber_days_before_target: int = Field(ge=0)
    stale_after_days: int = Field(gt=0)


class AppSettings(_Section):
    name: str


class LoggingSettings(_Section):
    level: str
    directory: str

    @field_validator("level")
    @classmethod
    def _valid_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in LOG_LEVELS:
            raise ValueError(f"invalid log level: {value!r}")
        return upper


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
        env_prefix="JIRA_DASHBOARD_",
        env_nested_delimiter="__",
    )

    jira: JiraSettings
    fields: FieldMapping
    working_time: WorkingTime
    requester: RequesterTemplate
    issues: IssueSettings
    boards: BoardMaps
    risk: RiskThresholds
    app: AppSettings
    logging: LoggingSettings

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        local = Path(os.environ.get(LOCAL_FILE_ENV, LOCAL_FILE_DEFAULT))
        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        if local.is_file():
            sources.append(TomlConfigSettingsSource(settings_cls, toml_file=local))
        sources.append(TomlConfigSettingsSource(settings_cls, toml_file=DEFAULT_TOML))
        return tuple(sources)


def get_settings() -> Settings:
    return Settings()
