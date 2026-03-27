"""In-memory implementation of SystemSettingsRepository for testing."""

from __future__ import annotations

from shared.domain.system_settings import SystemSettings
from shared.domain.system_settings_repository import SystemSettingsRepository


class InMemorySystemSettingsRepository(SystemSettingsRepository):
    """In-memory stub for SystemSettingsRepository."""

    def __init__(self) -> None:
        self._entity = SystemSettings()

    async def get(self) -> SystemSettings:
        return self._entity

    async def get_for_update(self) -> SystemSettings:
        return self._entity

    async def save(self, entity: SystemSettings) -> None:
        self._entity = entity
