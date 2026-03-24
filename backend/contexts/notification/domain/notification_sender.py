"""NotificationSender abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contexts.notification.domain.notification_message import NotificationMessage
from shared.domain.value_objects import UserId


class NotificationSender(ABC):
    """Abstract interface for sending notifications.

    Implementations handle the actual delivery mechanism (e.g. Slack API).
    """

    @abstractmethod
    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        """Send a notification to the given recipient.

        Args:
            recipient_id: The user to notify.
            message: The notification content.

        Raises:
            Exception: Implementation-specific delivery errors.
        """
