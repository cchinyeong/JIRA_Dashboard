from dataclasses import dataclass
from enum import StrEnum


class FindingCode(StrEnum):
    NON_STANDARD_STATUS = "NON_STANDARD_STATUS"
    TASK_WITHOUT_PARENT = "TASK_WITHOUT_PARENT"
    REQUEST_WRONG_EPIC_LINK = "REQUEST_WRONG_EPIC_LINK"
    INVALID_VALUE = "INVALID_VALUE"


@dataclass(frozen=True, slots=True)
class Finding:
    code: FindingCode
    message: str
    field: str | None = None
    related_key: str | None = None
    suggestion: str | None = None
