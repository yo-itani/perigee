from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.infrastructure.tables import NotificationSettingTable
from shared.domain.value_objects import UserId


class SqlAlchemyNotificationSettingRepository(NotificationSettingRepository):
    """SQLAlchemy-based implementation of NotificationSettingRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UserId) -> NotificationSetting | None:
        stmt = select(NotificationSettingTable).where(
            NotificationSettingTable.user_id == str(user_id.value)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: NotificationSetting) -> None:
        stmt = select(NotificationSettingTable).where(
            NotificationSettingTable.user_id == str(entity.user_id.value)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            row = NotificationSettingTable(
                id=str(uuid.uuid4()),
                user_id=str(entity.user_id.value),
                reminder_minutes_before=entity.reminder_minutes_before,
                is_enabled=entity.is_enabled,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            self._session.add(row)
        else:
            existing.reminder_minutes_before = entity.reminder_minutes_before
            existing.is_enabled = entity.is_enabled
            existing.updated_at = entity.updated_at

        await self._session.flush()

    @staticmethod
    def _to_entity(row: NotificationSettingTable) -> NotificationSetting:
        return NotificationSetting(
            user_id=UserId.from_str(row.user_id),
            _reminder_minutes_before=row.reminder_minutes_before,
            _is_enabled=row.is_enabled,
            created_at=row.created_at,
            _updated_at=row.updated_at,
        )
