"""Handler for ScheduleCreated events."""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.events import ScheduleCreated
from contexts.preparation.domain.schedule_repository import ScheduleRepository

logger = logging.getLogger(__name__)


class ScheduleCreatedHandler:
    """Notify the counterpart when a schedule is created.

    Re-fetches the schedule from the repository to obtain the counterpart_id.
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

    async def __call__(self, event: ScheduleCreated) -> None:
        schedule = await self._schedule_repo.get_by_id(event.schedule_id)
        if schedule is None:
            logger.warning(
                "Schedule %s not found for ScheduleCreated notification",
                event.schedule_id,
            )
            return

        recipient_id = schedule.counterpart_id

        if not await self._setting_repo.is_enabled(recipient_id):
            return

        message = NotificationMessage(
            notification_type=NotificationType.SCHEDULE_CREATED,
            title="New 1-on-1 scheduled",
            body="A new 1-on-1 has been scheduled with you.",
        )
        try:
            await self._sender.send(recipient_id, message)
        except Exception:
            logger.exception(
                "Failed to send ScheduleCreated notification to %s",
                recipient_id,
            )
