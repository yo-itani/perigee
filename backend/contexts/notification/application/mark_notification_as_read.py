"""Use case: Mark a notification as read.

Marks a single notification record as read for the authenticated user.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.notification.domain.exceptions import UnauthorizedOperationError
from contexts.notification.domain.notification_record_repository import (
    NotificationRecordRepository,
)
from contexts.notification.domain.value_objects import NotificationRecordId
from foundation.application.unit_of_work import UnitOfWork
from shared.domain.value_objects import UserId


class NotificationNotFoundError(Exception):
    """Raised when the specified notification record does not exist."""

    def __init__(self, message: str = "Notification not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class MarkNotificationAsReadInput:
    """Input DTO for MarkNotificationAsReadUseCase."""

    notification_id: NotificationRecordId
    actor_id: UserId


class MarkNotificationAsReadUseCase:
    """Mark a notification as read.

    Workflow:
    1. Load the notification record.
    2. Verify the actor is the recipient.
    3. Mark as read.
    4. Save within a transaction.
    """

    def __init__(
        self,
        *,
        notification_record_repository: NotificationRecordRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._notification_record_repository = notification_record_repository
        self._unit_of_work = unit_of_work

    async def execute(self, input_dto: MarkNotificationAsReadInput) -> None:
        async with self._unit_of_work:
            record = await self._notification_record_repository.get_by_id(
                input_dto.notification_id
            )

            if record is None:
                raise NotificationNotFoundError(
                    f"Notification {input_dto.notification_id.value} not found."
                )

            if record.recipient_id != input_dto.actor_id:
                raise UnauthorizedOperationError(
                    "Cannot mark another user's notification as read."
                )

            now = datetime.now(UTC)
            record.mark_as_read(now=now)

            await self._notification_record_repository.save(record)
