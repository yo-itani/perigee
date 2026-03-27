"""Tests for GetSystemStatusQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shared.application.get_system_status_query_service import (
    GetSystemStatusQueryService,
)
from shared.domain.system_settings import SystemSettings
from shared.infrastructure.in_memory_system_settings_repository import (
    InMemorySystemSettingsRepository,
)


@pytest.fixture
def system_settings_repo() -> InMemorySystemSettingsRepository:
    return InMemorySystemSettingsRepository()


@pytest.fixture
def query_service(
    system_settings_repo: InMemorySystemSettingsRepository,
) -> GetSystemStatusQueryService:
    return GetSystemStatusQueryService(system_settings_repo=system_settings_repo)


@pytest.mark.asyncio
async def test_setup_not_complete_when_not_marked(
    query_service: GetSystemStatusQueryService,
) -> None:
    """is_setup_complete is False when setup_completed_at is None."""
    output = await query_service.execute()
    assert output.is_setup_complete is False


@pytest.mark.asyncio
async def test_setup_complete_when_marked(
    system_settings_repo: InMemorySystemSettingsRepository,
    query_service: GetSystemStatusQueryService,
) -> None:
    """is_setup_complete is True when setup has been marked complete."""
    settings = SystemSettings()
    settings.mark_setup_complete(datetime.now(UTC))
    await system_settings_repo.save(settings)

    output = await query_service.execute()
    assert output.is_setup_complete is True
