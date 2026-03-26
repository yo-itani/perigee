"""Application service: send reminder notifications for upcoming 1-on-1s.

Called periodically by the scheduler. For each CONFIRMED schedule whose
reminder window has opened, sends a notification to eligible participants
and records a ReminderLog to prevent duplicates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.reminder_log import ReminderLog
from contexts.notification.domain.reminder_log_repository import ReminderLogRepository
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from shared.domain.value_objects import UserId

logger = logging.getLogger(__name__)

_MAX_REMINDER_MINUTES = 1440


class SendReminderUseCase:
    """Send reminder notifications for upcoming confirmed schedules.

    Processing flow:
    1. Fetch CONFIRMED schedules in the lookahead window.
    2. For each participant (organizer + counterpart):
       a. Check notification is enabled.
       b. Check reminder window: scheduled_at - reminder_minutes <= now.
       c. Check ReminderLog does not already exist.
       d. Send notification and save ReminderLog.

    Note: The caller is responsible for providing repositories that share
    the same DB session, and for committing after each save if needed.
    """

    def __init__(
        self,
        *,
        schedule_repository: ScheduleRepository,
        notification_setting_repository: NotificationSettingRepository,
        reminder_log_repository: ReminderLogRepository,
        notification_sender: NotificationSender,
    ) -> None:
        self._schedule_repo = schedule_repository
        self._setting_repo = notification_setting_repository
        self._reminder_log_repo = reminder_log_repository
        self._sender = notification_sender

    async def execute(self, now: datetime) -> None:
        """Run one cycle of reminder checks and sends."""
        schedules = await self._schedule_repo.list_confirmed_upcoming(
            now, _MAX_REMINDER_MINUTES
        )

        for schedule in schedules:
            participants = [schedule.organizer_id, schedule.counterpart_id]
            for user_id in participants:
                try:
                    await self._process_participant(schedule, user_id, now)
                except Exception:
                    logger.exception(
                        "Failed to process reminder for schedule=%s user=%s",
                        schedule.id,
                        user_id,
                    )

    async def _process_participant(
        self, schedule: Schedule, user_id: UserId, now: datetime
    ) -> None:
        """Check and send reminder for a single participant."""
        setting = await self._setting_repo.get_by_user_id(user_id)
        if setting is None:
            setting = NotificationSetting.create_default(user_id)

        if not setting.is_enabled:
            return

        reminder_minutes = setting.reminder_minutes_before
        # Normalize tz-aware/naive: scheduled_at from DB is tz-naive (UTC),
        # while now may be tz-aware. Strip tzinfo to compare consistently.
        scheduled_at = schedule.scheduled_at
        comparable_now = now.replace(tzinfo=None) if now.tzinfo is not None else now
        comparable_scheduled_at = (
            scheduled_at.replace(tzinfo=None)
            if scheduled_at.tzinfo is not None
            else scheduled_at
        )
        reminder_threshold = comparable_scheduled_at - timedelta(
            minutes=reminder_minutes
        )
        if reminder_threshold > comparable_now:
            return

        already_sent = await self._reminder_log_repo.exists(
            schedule.id, user_id, schedule.scheduled_at
        )
        if already_sent:
            return

        message = NotificationMessage(
            notification_type=NotificationType.REMINDER,
            title="1-on-1 reminder",
            body=(
                f"Your 1-on-1 '{schedule.title.value}' is scheduled "
                f"in {reminder_minutes} minutes."
            ),
        )

        await self._sender.send(user_id, message)

        log = ReminderLog.create(
            schedule_id=schedule.id,
            user_id=user_id,
            scheduled_at=schedule.scheduled_at,
            reminder_minutes_before=reminder_minutes,
            now=now,
        )
        await self._reminder_log_repo.save(log)
