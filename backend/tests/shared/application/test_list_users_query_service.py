"""Tests for ListUsersQueryService."""

from __future__ import annotations

import pytest

from shared.application.list_users_query_service import (
    ListUsersInput,
    ListUsersQueryService,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def service(repo: InMemoryUserRepository) -> ListUsersQueryService:
    return ListUsersQueryService(user_repo=repo)


@pytest.mark.asyncio
async def test_list_empty(service: ListUsersQueryService) -> None:
    """An empty repository returns an empty list."""
    output = await service.execute()
    assert output.users == []


@pytest.mark.asyncio
async def test_list_users(
    repo: InMemoryUserRepository, service: ListUsersQueryService
) -> None:
    """All users are returned."""
    repo.add(
        User(
            id=UserId.generate(),
            name="Alice",
            email="alice@example.com",
            role=UserRole.MEMBER,
        )
    )
    repo.add(
        User(
            id=UserId.generate(),
            name="Bob",
            email="bob@example.com",
            role=UserRole.ADMIN,
        )
    )

    output = await service.execute()
    assert len(output.users) == 2
    names = {u.name for u in output.users}
    assert names == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_list_users_with_pagination(
    repo: InMemoryUserRepository, service: ListUsersQueryService
) -> None:
    """Pagination returns the correct subset of users."""
    for i in range(5):
        repo.add(
            User(
                id=UserId.generate(),
                name=f"User{i:02d}",
                email=f"user{i}@example.com",
                role=UserRole.MEMBER,
            )
        )

    # First page
    output = await service.execute(ListUsersInput(offset=0, limit=2))
    assert len(output.users) == 2
    assert output.users[0].name == "User00"
    assert output.users[1].name == "User01"

    # Second page
    output = await service.execute(ListUsersInput(offset=2, limit=2))
    assert len(output.users) == 2
    assert output.users[0].name == "User02"
    assert output.users[1].name == "User03"

    # Last page (partial)
    output = await service.execute(ListUsersInput(offset=4, limit=2))
    assert len(output.users) == 1
    assert output.users[0].name == "User04"

    # Beyond range
    output = await service.execute(ListUsersInput(offset=10, limit=2))
    assert len(output.users) == 0
