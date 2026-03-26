from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class UserId:
    """User identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> UserId:
        return UserId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> UserId:
        return UserId(value=uuid.UUID(raw))


class UserRole(StrEnum):
    """User role in the system."""

    ADMIN = "admin"
    MEMBER = "member"
