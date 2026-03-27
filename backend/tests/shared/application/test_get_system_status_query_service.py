"""Tests for GetSystemStatusQueryService."""

from __future__ import annotations

import pytest

from shared.application.get_system_status_query_service import (
    GetSystemStatusQueryService,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def query_service(repo: InMemoryUserRepository) -> GetSystemStatusQueryService:
    return GetSystemStatusQueryService(user_repo=repo)


@pytest.mark.asyncio
async def test_setup_not_complete_when_no_users(
    query_service: GetSystemStatusQueryService,
) -> None:
    """is_setup_complete is False when the users table is empty."""
    output = await query_service.execute()
    assert output.is_setup_complete is False


@pytest.mark.asyncio
async def test_setup_complete_when_users_exist(
    repo: InMemoryUserRepository,
    query_service: GetSystemStatusQueryService,
) -> None:
    """is_setup_complete is True when at least one user exists."""
    repo.add(
        User(
            id=UserId.generate(),
            name="Admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
    )
    output = await query_service.execute()
    assert output.is_setup_complete is True
