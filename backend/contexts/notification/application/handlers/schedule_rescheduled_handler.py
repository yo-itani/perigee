"""Handler for ScheduleRescheduled events."""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.events import ScheduleRescheduled
from contexts.preparation.domain.schedule_repository import ScheduleRepository

logger = logging.getLogger(__name__)


class ScheduleRescheduledHandler:
    """Notify the other party when a schedule is rescheduled.

    Uses ``requested_by`` from the event to determine who initiated the
    reschedule, then notifies the other participant.
    """

    def __init__(
        self,
        *,
        schedule_repository: ScheduleRepository,
        notification_sender: NotificationSender,
        notification_setting_repository: NotificationSettingRepository,
    ) -> None:
        self._schedule_repo = schedule_repository
        self._sender = notification_sender
        self._setting_repo = notification_setting_repository

    async def __call__(self, event: ScheduleRescheduled) -> None:
        schedule = await self._schedule_repo.get_by_id(event.schedule_id)
        if schedule is None:
            logger.warning(
                "Schedule %s not found for ScheduleRescheduled notification",
                event.schedule_id,
            )
            return

        # Notify the party who did NOT request the reschedule
        if event.requested_by == schedule.organizer_id:
            recipient_id = schedule.counterpart_id
        else:
            recipient_id = schedule.organizer_id

        if not await self._setting_repo.is_enabled(recipient_id):
            return

        message = NotificationMessage(
            notification_type=NotificationType.SCHEDULE_RESCHEDULED,
            title="1-on-1 rescheduled",
            body="The 1-on-1 schedule has been changed.",
        )
        try:
            await self._sender.send(recipient_id, message)
        except Exception:
            logger.exception(
                "Failed to send ScheduleRescheduled notification to %s",
                recipient_id,
            )
