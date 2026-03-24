"""ReminderLog entity for tracking sent reminders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.notification.domain.value_objects import ReminderLogId
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId


@dataclass
class ReminderLog:
    """Entity: records that a reminder was sent for a specific schedule/user/time.

    The composite key (schedule_id, user_id, scheduled_at) prevents duplicate
    reminders. Including scheduled_at allows re-sending reminders when a
    schedule is rescheduled to a new datetime.
    """

    id: ReminderLogId
    schedule_id: ScheduleId
    user_id: UserId
    scheduled_at: datetime
    _sent_at: datetime
    _reminder_minutes_before: int

    @property
    def sent_at(self) -> datetime:
        return self._sent_at

    @property
    def reminder_minutes_before(self) -> int:
        return self._reminder_minutes_before

    @staticmethod
    def create(
        *,
        schedule_id: ScheduleId,
        user_id: UserId,
        scheduled_at: datetime,
        reminder_minutes_before: int,
        now: datetime | None = None,
    ) -> ReminderLog:
        """Create a new reminder log entry."""
        ts = now or datetime.now(UTC)
        return ReminderLog(
            id=ReminderLogId.generate(),
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=scheduled_at,
            _sent_at=ts,
            _reminder_minutes_before=reminder_minutes_before,
        )
