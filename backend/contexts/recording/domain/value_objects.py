from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from contexts.recording.domain.exceptions import InvalidActionItemTitleError

_ACTION_ITEM_TITLE_MAX_LENGTH = 200


@dataclass(frozen=True)
class ActionItemTitle:
    """Value object for action item title.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Must not contain newlines.
    - Max 200 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, raw: str) -> None:
        stripped = raw.strip()
        if not stripped:
            raise InvalidActionItemTitleError("Action item title must not be empty.")
        if "\n" in stripped or "\r" in stripped:
            raise InvalidActionItemTitleError(
                "Action item title must not contain newlines."
            )
        if len(stripped) > _ACTION_ITEM_TITLE_MAX_LENGTH:
            raise InvalidActionItemTitleError(
                f"Action item title must not exceed"
                f" {_ACTION_ITEM_TITLE_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RecordId:
    """Record identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> RecordId:
        return RecordId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> RecordId:
        return RecordId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class ActionItemId:
    """ActionItem identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> ActionItemId:
        return ActionItemId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ActionItemId:
        return ActionItemId(value=uuid.UUID(raw))


class RecordStatus(Enum):
    """Record status: Draft -> Published (one-way transition)."""

    DRAFT = "draft"
    PUBLISHED = "published"
