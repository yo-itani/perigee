"""Tests for GetUserDetailQueryService."""

from __future__ import annotations

import pytest

from shared.application.get_user_detail_query_service import (
    GetUserDetailInput,
    GetUserDetailQueryService,
    UserNotFoundError,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def service(repo: InMemoryUserRepository) -> GetUserDetailQueryService:
    return GetUserDetailQueryService(user_repo=repo)


@pytest.mark.asyncio
async def test_get_user_detail_success(
    repo: InMemoryUserRepository, service: GetUserDetailQueryService
) -> None:
    """A user's detail is returned by ID."""
    user = User(
        id=UserId.generate(),
        name="Alice",
        email="alice@example.com",
        role=UserRole.MEMBER,
        slack_user_id="U123",
    )
    repo.add(user)

    output = await service.execute(GetUserDetailInput(user_id=user.id))
    assert output.name == "Alice"
    assert output.email == "alice@example.com"
    assert output.role == UserRole.MEMBER
    assert output.slack_user_id == "U123"


@pytest.mark.asyncio
async def test_get_user_detail_not_found(
    service: GetUserDetailQueryService,
) -> None:
    """Requesting a non-existent user raises UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await service.execute(GetUserDetailInput(user_id=UserId.generate()))
