"""Tests for ReminderLog entity."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.domain.reminder_log import ReminderLog
from contexts.notification.domain.value_objects import ReminderLogId
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId

NOW = datetime(2026, 3, 25, 10, 0)
SCHEDULED_AT = datetime(2026, 4, 1, 10, 0)


class TestReminderLog:
    """Tests for ReminderLog entity creation."""

    def test_create_sets_fields(self) -> None:
        schedule_id = ScheduleId.generate()
        user_id = UserId.generate()

        log = ReminderLog.create(
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=SCHEDULED_AT,
            reminder_minutes_before=30,
            now=NOW,
        )

        assert log.schedule_id == schedule_id
        assert log.user_id == user_id
        assert log.scheduled_at == SCHEDULED_AT
        assert log.sent_at == NOW
        assert log.reminder_minutes_before == 30
        assert isinstance(log.id, ReminderLogId)

    def test_create_generates_unique_ids(self) -> None:
        schedule_id = ScheduleId.generate()
        user_id = UserId.generate()

        log1 = ReminderLog.create(
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=SCHEDULED_AT,
            reminder_minutes_before=30,
            now=NOW,
        )
        log2 = ReminderLog.create(
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=SCHEDULED_AT,
            reminder_minutes_before=30,
            now=NOW,
        )

        assert log1.id != log2.id
