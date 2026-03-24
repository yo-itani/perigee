from __future__ import annotations

from dataclasses import dataclass

from contexts.record.domain.exceptions import InvalidRetrospectiveBodyError

_RETROSPECTIVE_BODY_MAX_LENGTH = 2000


@dataclass(frozen=True)
class RetrospectiveBody:
    """Value object representing a retrospective body string.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Max 2000 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidRetrospectiveBodyError("Retrospective body must not be empty.")
        if len(stripped) > _RETROSPECTIVE_BODY_MAX_LENGTH:
            raise InvalidRetrospectiveBodyError(
                f"Retrospective body must not exceed"
                f" {_RETROSPECTIVE_BODY_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
