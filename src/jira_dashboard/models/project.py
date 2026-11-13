from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Project:
    key: str
    name: str
