from __future__ import annotations

from dataclasses import dataclass

from contexts.preparation.domain.exceptions import InvalidTopicError

_TOPIC_MAX_LENGTH = 200


@dataclass(frozen=True)
class Topic:
    """Value object representing an agenda topic string.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Must not contain newlines.
    - Max 200 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidTopicError("Topic must not be empty.")
        if "\n" in stripped or "\r" in stripped:
            raise InvalidTopicError("Topic must not contain newlines.")
        if len(stripped) > _TOPIC_MAX_LENGTH:
            raise InvalidTopicError(
                f"Topic must not exceed {_TOPIC_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
