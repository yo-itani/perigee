"""Use case: Get a user's notification setting.

Returns the persisted setting if it exists, otherwise returns
a default setting (not persisted to DB).
"""

from __future__ import annotations

from dataclasses import dataclass

from contexts.notification.domain.exceptions import UnauthorizedOperationError
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class GetNotificationSettingInput:
    """Input DTO for GetNotificationSettingUseCase."""

    user_id: UserId
    actor_id: UserId


@dataclass(frozen=True)
class GetNotificationSettingOutput:
    """Output DTO for GetNotificationSettingUseCase."""

    user_id: UserId
    reminder_minutes_before: int
    is_enabled: bool


class GetNotificationSettingUseCase:
    """Get the notification setting for a user.

    If the user has no persisted setting, return default values
    without saving to DB.
    """

    def __init__(
        self,
        *,
        notification_setting_repository: NotificationSettingRepository,
    ) -> None:
        self._notification_setting_repository = notification_setting_repository

    async def execute(
        self, input_dto: GetNotificationSettingInput
    ) -> GetNotificationSettingOutput:
        if input_dto.actor_id != input_dto.user_id:
            raise UnauthorizedOperationError(
                "Cannot access another user's notification setting."
            )

        setting = await self._notification_setting_repository.get_by_user_id(
            input_dto.user_id
        )

        if setting is None:
            setting = NotificationSetting.create_default(input_dto.user_id)

        return GetNotificationSettingOutput(
            user_id=setting.user_id,
            reminder_minutes_before=setting.reminder_minutes_before,
            is_enabled=setting.is_enabled,
        )
