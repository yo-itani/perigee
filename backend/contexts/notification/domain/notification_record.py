"""NotificationRecord entity for tracking user notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.notification.domain.exceptions import NotificationAlreadyReadError
from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.value_objects import (
    NotificationRecordId,
    NotificationType,
)
from shared.domain.value_objects import UserId


@dataclass
class NotificationRecord:
    """Entity: a notification sent to a user.

    Tracks whether the notification has been read.

    Business rules:
    - A notification cannot be marked as read if it is already read.
    """

    id: NotificationRecordId
    recipient_id: UserId
    notification_type: NotificationType
    title: str
    body: str
    link: str | None
    _is_read: bool
    _read_at: datetime | None
    created_at: datetime

    @property
    def is_read(self) -> bool:
        return self._is_read

    @property
    def read_at(self) -> datetime | None:
        return self._read_at

    @staticmethod
    def create(
        *,
        recipient_id: UserId,
        message: NotificationMessage,
        now: datetime | None = None,
    ) -> NotificationRecord:
        """Create a new unread notification record."""
        ts = now or datetime.now(UTC)
        return NotificationRecord(
            id=NotificationRecordId.generate(),
            recipient_id=recipient_id,
            notification_type=message.notification_type,
            title=message.title,
            body=message.body,
            link=message.link,
            _is_read=False,
            _read_at=None,
            created_at=ts,
        )

    def mark_as_read(self, now: datetime) -> None:
        """Mark this notification as read.

        Raises:
            NotificationAlreadyReadError: If the notification is already read.
        """
        if self._is_read:
            raise NotificationAlreadyReadError(
                f"Notification {self.id.value} is already marked as read."
            )
        self._is_read = True
        self._read_at = now
