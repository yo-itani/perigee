"""Repository interface for SystemSettings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.system_settings import SystemSettings


class SystemSettingsRepository(ABC):
    """Interface for SystemSettings persistence."""

    @abstractmethod
    async def get(self) -> SystemSettings:
        """Return the singleton SystemSettings row."""
        ...

    @abstractmethod
    async def get_for_update(self) -> SystemSettings:
        """Return the singleton SystemSettings row with a row-level lock.

        Uses SELECT ... FOR UPDATE to prevent concurrent modifications.
        """
        ...

    @abstractmethod
    async def save(self, entity: SystemSettings) -> None:
        """Persist the SystemSettings entity."""
        ...
