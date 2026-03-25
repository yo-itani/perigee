"""NotificationRecordRepository abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.value_objects import NotificationRecordId
from shared.domain.value_objects import UserId


class NotificationRecordRepository(ABC):
    """Repository interface for NotificationRecord."""

    @abstractmethod
    async def get_by_id(
        self, record_id: NotificationRecordId
    ) -> NotificationRecord | None:
        """Return the notification record with the given id, or None."""

    @abstractmethod
    async def list_by_recipient(
        self,
        recipient_id: UserId,
        *,
        unread_only: bool = False,
    ) -> list[NotificationRecord]:
        """Return notification records for the given recipient.

        Args:
            recipient_id: The user whose notifications to retrieve.
            unread_only: If True, return only unread notifications.

        Returns:
            List of notification records, ordered by created_at descending.
        """

    @abstractmethod
    async def save(self, record: NotificationRecord) -> None:
        """Persist the notification record (insert or update)."""
