"""Use case: Update a user's notification setting.

Creates or updates the notification setting for the acting user.
On first update, the setting is newly created (upsert via repository).
Dispatches NotificationSettingUpdated event after successful commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.notification.domain.exceptions import UnauthorizedOperationError
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class UpdateNotificationSettingInput:
    """Input DTO for UpdateNotificationSettingUseCase."""

    user_id: UserId
    actor_id: UserId
    reminder_minutes_before: int
    is_enabled: bool


@dataclass(frozen=True)
class UpdateNotificationSettingOutput:
    """Output DTO for UpdateNotificationSettingUseCase."""

    user_id: UserId
    reminder_minutes_before: int
    is_enabled: bool


class UpdateNotificationSettingUseCase:
    """Update (or create) the notification setting for a user.

    Workflow:
    1. Verify the actor is the setting owner.
    2. Load existing setting or create default.
    3. Apply the update (validation in domain, event emitted).
    4. Save (upsert) within a transaction.
    5. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        notification_setting_repository: NotificationSettingRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._notification_setting_repository = notification_setting_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(
        self, input_dto: UpdateNotificationSettingInput
    ) -> UpdateNotificationSettingOutput:
        if input_dto.actor_id != input_dto.user_id:
            raise UnauthorizedOperationError(
                "Cannot modify another user's notification setting."
            )

        now = datetime.now(UTC)

        async with self._unit_of_work:
            setting = await self._notification_setting_repository.get_by_user_id(
                input_dto.user_id
            )

            if setting is None:
                setting = NotificationSetting.create_default(input_dto.user_id, now=now)

            setting.update(
                reminder_minutes_before=input_dto.reminder_minutes_before,
                is_enabled=input_dto.is_enabled,
                now=now,
            )

            await self._notification_setting_repository.save(setting)
            events: list[DomainEvent] = list(setting.collect_events())
            await self._unit_of_work.commit()

        await self._event_dispatcher.dispatch(events)

        return UpdateNotificationSettingOutput(
            user_id=setting.user_id,
            reminder_minutes_before=setting.reminder_minutes_before,
            is_enabled=setting.is_enabled,
        )
