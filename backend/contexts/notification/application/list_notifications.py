"""Use case: List notifications for a user.

Returns the user's notification records, optionally filtered to unread only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contexts.notification.domain.notification_record_repository import (
    NotificationRecordRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class ListNotificationsInput:
    """Input DTO for ListNotificationsUseCase."""

    actor_id: UserId
    unread_only: bool = False


@dataclass(frozen=True)
class NotificationRecordOutput:
    """Output DTO for a single notification record."""

    id: UUID
    recipient_id: UserId
    notification_type: NotificationType
    title: str
    body: str
    link: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class ListNotificationsOutput:
    """Output DTO for ListNotificationsUseCase."""

    notifications: list[NotificationRecordOutput]


class ListNotificationsUseCase:
    """List notifications for the authenticated user."""

    def __init__(
        self,
        *,
        notification_record_repository: NotificationRecordRepository,
    ) -> None:
        self._notification_record_repository = notification_record_repository

    async def execute(
        self, input_dto: ListNotificationsInput
    ) -> ListNotificationsOutput:
        records = await self._notification_record_repository.list_by_recipient(
            input_dto.actor_id,
            unread_only=input_dto.unread_only,
        )

        return ListNotificationsOutput(
            notifications=[
                NotificationRecordOutput(
                    id=r.id.value,
                    recipient_id=r.recipient_id,
                    notification_type=r.notification_type,
                    title=r.title,
                    body=r.body,
                    link=r.link,
                    is_read=r.is_read,
                    read_at=r.read_at,
                    created_at=r.created_at,
                )
                for r in records
            ]
        )
