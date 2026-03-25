"""NotificationSender decorator that persists a NotificationRecord on send."""

from __future__ import annotations

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.notification_record_repository import (
    NotificationRecordRepository,
)
from contexts.notification.domain.notification_sender import NotificationSender
from shared.domain.value_objects import UserId


class RecordingNotificationSender(NotificationSender):
    """Decorator that saves a NotificationRecord before delegating to the inner sender.

    This ensures every sent notification is tracked in the database
    for the unread notifications list (GET /notifications?unread=true).
    """

    def __init__(
        self,
        *,
        inner: NotificationSender,
        notification_record_repository: NotificationRecordRepository,
    ) -> None:
        self._inner = inner
        self._record_repo = notification_record_repository

    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        """Save a NotificationRecord and then send the notification."""
        record = NotificationRecord.create(
            recipient_id=recipient_id,
            message=message,
        )
        await self._record_repo.save(record)
        await self._inner.send(recipient_id, message)
