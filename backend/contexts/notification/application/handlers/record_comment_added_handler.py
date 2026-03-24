"""Handler for RecordCommentAdded events."""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.record.domain.events import RecordCommentAdded
from contexts.record.domain.record_repository import RecordRepository

logger = logging.getLogger(__name__)


class RecordCommentAddedHandler:
    """Notify relevant parties when a comment is added to a published record.

    Notification policy:
    - If organizer or counterpart comments -> notify the other party only
      (viewers are NOT notified).
    - If a viewer comments -> notify both organizer and counterpart.
    - The comment author is never notified.
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

    async def __call__(self, event: RecordCommentAdded) -> None:
        record = await self._record_repo.get_by_id(event.record_id)
        if record is None:
            logger.warning(
                "Record %s not found for RecordCommentAdded notification",
                event.record_id,
            )
            return

        author = event.author_id
        organizer = record.organizer_id
        counterpart = record.counterpart_id

        is_principal = author in (organizer, counterpart)

        if is_principal:
            # Organizer or counterpart commented -> notify the other one only
            recipients = [counterpart] if author == organizer else [organizer]
        else:
            # Viewer commented -> notify both organizer and counterpart
            recipients = [organizer, counterpart]

        message = NotificationMessage(
            notification_type=NotificationType.RECORD_COMMENT_ADDED,
            title="New comment on record",
            body="A new comment has been added to a 1-on-1 record.",
        )

        for recipient_id in recipients:
            if not await self._setting_repo.is_enabled(recipient_id):
                continue
            try:
                await self._sender.send(recipient_id, message)
            except Exception:
                logger.exception(
                    "Failed to send RecordCommentAdded notification to %s",
                    recipient_id,
                )
