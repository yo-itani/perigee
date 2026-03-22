from __future__ import annotations

from dataclasses import dataclass

from contexts.preparation.domain.exceptions import InvalidScheduleTitleError

_SCHEDULE_TITLE_MAX_LENGTH = 100


@dataclass(frozen=True)
class ScheduleTitle:
    """Value object representing a schedule title string.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Max 100 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidScheduleTitleError("Schedule title must not be empty.")
        if len(stripped) > _SCHEDULE_TITLE_MAX_LENGTH:
            raise InvalidScheduleTitleError(
                f"Schedule title must not exceed "
                f"{_SCHEDULE_TITLE_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
