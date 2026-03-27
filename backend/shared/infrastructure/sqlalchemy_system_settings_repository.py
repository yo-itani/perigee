"""SQLAlchemy implementation of SystemSettingsRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.domain.system_settings import SystemSettings
from shared.domain.system_settings_repository import SystemSettingsRepository
from shared.infrastructure.tables import SystemSettingsTable


class SqlAlchemySystemSettingsRepository(SystemSettingsRepository):
    """SQLAlchemy-based implementation of SystemSettingsRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SystemSettings:
        stmt = select(SystemSettingsTable).where(SystemSettingsTable.id == 1)
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        return self._to_entity(row)

    async def get_for_update(self) -> SystemSettings:
        stmt = (
            select(SystemSettingsTable)
            .where(SystemSettingsTable.id == 1)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        return self._to_entity(row)

    async def save(self, entity: SystemSettings) -> None:
        existing = await self._session.get(SystemSettingsTable, 1)
        if existing is not None:
            existing.setup_completed_at = entity.setup_completed_at
            await self._session.flush()

    @staticmethod
    def _to_entity(row: SystemSettingsTable) -> SystemSettings:
        return SystemSettings(
            setup_completed_at=row.setup_completed_at,
        )
