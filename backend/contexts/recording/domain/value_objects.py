from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


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
