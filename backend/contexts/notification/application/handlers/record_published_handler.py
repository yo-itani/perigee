"""Handler for RecordPublished events."""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.record.domain.events import RecordPublished
from contexts.record.domain.record_repository import RecordRepository

logger = logging.getLogger(__name__)


class RecordPublishedHandler:
    """Notify the counterpart and all viewers when a record is published.

    The organizer (who published) is excluded from notifications.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        notification_sender: NotificationSender,
        notification_setting_repository: NotificationSettingRepository,
    ) -> None:
        self._record_repo = record_repository
        self._sender = notification_sender
        self._setting_repo = notification_setting_repository

    async def __call__(self, event: RecordPublished) -> None:
        record = await self._record_repo.get_by_id(event.record_id)
        if record is None:
            logger.warning(
                "Record %s not found for RecordPublished notification",
                event.record_id,
            )
            return

        # Counterpart + all explicit viewers
        recipients = [record.counterpart_id, *record.viewers]

        message = NotificationMessage(
            notification_type=NotificationType.RECORD_PUBLISHED,
            title="1-on-1 record published",
            body="A 1-on-1 record has been published.",
        )

        for recipient_id in recipients:
            if not await self._setting_repo.is_enabled(recipient_id):
                continue
            try:
                await self._sender.send(recipient_id, message)
            except Exception:
                logger.exception(
                    "Failed to send RecordPublished notification to %s",
                    recipient_id,
                )
