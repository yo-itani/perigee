from __future__ import annotations

from dataclasses import dataclass

from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class NotificationSettingUpdated(DomainEvent):
    """Raised when a user's notification setting is updated."""

    user_id: UserId
    reminder_minutes_before: int
    is_enabled: bool
