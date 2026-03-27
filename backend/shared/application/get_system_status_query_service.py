"""Query service: check whether initial setup has been completed."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.system_settings_repository import SystemSettingsRepository


@dataclass(frozen=True)
class GetSystemStatusOutput:
    is_setup_complete: bool


class GetSystemStatusQueryService:
    """Return whether the system setup has been completed."""

    def __init__(self, system_settings_repo: SystemSettingsRepository) -> None:
        self._system_settings_repo = system_settings_repo

    async def execute(self) -> GetSystemStatusOutput:
        settings = await self._system_settings_repo.get()
        return GetSystemStatusOutput(is_setup_complete=settings.is_setup_complete)
