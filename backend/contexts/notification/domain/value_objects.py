"""Value objects for the Notification bounded context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    """Types of notification triggers."""

    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_RESCHEDULED = "schedule_rescheduled"
    SCHEDULE_CANCELLED = "schedule_cancelled"
    RECORD_PUBLISHED = "record_published"
    AGENDA_COMMENT_ADDED = "agenda_comment_added"
    RECORD_COMMENT_ADDED = "record_comment_added"


@dataclass(frozen=True)
class NotificationSettingId:
    """Notification setting identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> NotificationSettingId:
        return NotificationSettingId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> NotificationSettingId:
        return NotificationSettingId(value=uuid.UUID(raw))
