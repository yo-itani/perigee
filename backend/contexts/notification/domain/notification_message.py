"""NotificationMessage value object."""

from __future__ import annotations

from dataclasses import dataclass

from contexts.notification.domain.value_objects import NotificationType


@dataclass(frozen=True)
class NotificationMessage:
    """Value object representing a notification to be sent.

    Attributes:
        notification_type: The type/trigger of this notification.
        title: Short summary of the notification.
        body: Detailed notification text.
        link: Optional deep-link URL for the notification target.
    """

    notification_type: NotificationType
    title: str
    body: str
    link: str | None = None
