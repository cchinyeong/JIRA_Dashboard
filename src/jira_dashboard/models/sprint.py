from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Sprint:
    id: int
    name: str
    state: str
    start_date: date | None = None
    end_date: date | None = None
