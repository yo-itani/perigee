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
