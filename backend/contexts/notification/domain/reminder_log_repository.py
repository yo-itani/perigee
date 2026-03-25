"""ReminderLogRepository abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from contexts.notification.domain.reminder_log import ReminderLog
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId


class ReminderLogRepository(ABC):
    """Repository interface for ReminderLog.

    Does not extend BaseRepository because the primary lookup
    is by composite key (schedule_id, user_id, scheduled_at),
    not by a single entity id.
    """

    @abstractmethod
    async def exists(
        self,
        schedule_id: ScheduleId,
        user_id: UserId,
        scheduled_at: datetime,
    ) -> bool:
        """Check if a reminder has already been sent for this combination."""

    @abstractmethod
    async def save(self, log: ReminderLog) -> None:
        """Persist the reminder log entry."""
