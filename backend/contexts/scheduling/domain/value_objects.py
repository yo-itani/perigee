from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduleId:
    """Schedule identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> ScheduleId:
        return ScheduleId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ScheduleId:
        return ScheduleId(value=uuid.UUID(raw))
