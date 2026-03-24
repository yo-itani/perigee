"""NotificationSettingRepository abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contexts.notification.domain.notification_setting import NotificationSetting
from shared.domain.value_objects import UserId


class NotificationSettingRepository(ABC):
    """Repository interface for NotificationSetting.

    Unlike BaseRepository, this uses user_id as the lookup key
    (one setting per user). save() performs upsert.
    """

    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> NotificationSetting | None:
        """Return the setting for the given user, or None if not found."""

    @abstractmethod
    async def save(self, entity: NotificationSetting) -> None:
        """Persist the setting (insert or update / upsert)."""

    async def is_enabled(self, user_id: UserId) -> bool:
        """Return whether notifications are enabled for the given user.

        If no explicit setting exists for the user, this returns
        ``True`` (notifications enabled by default).
        """
        setting = await self.get_by_user_id(user_id)
        if setting is None:
            return NotificationSetting.DEFAULT_IS_ENABLED
        return setting.is_enabled
