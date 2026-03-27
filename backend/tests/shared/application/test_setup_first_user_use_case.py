"""Tests for SetupFirstUserUseCase."""

from __future__ import annotations

import pytest

from shared.application.setup_first_user_use_case import (
    SetupAlreadyCompleteError,
    SetupFirstUserInput,
    SetupFirstUserUseCase,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def use_case(repo: InMemoryUserRepository) -> SetupFirstUserUseCase:
    return SetupFirstUserUseCase(user_repo=repo)


@pytest.mark.asyncio
async def test_setup_first_user_success(
    use_case: SetupFirstUserUseCase,
    repo: InMemoryUserRepository,
) -> None:
    """The first user is created with admin role when no users exist."""
    output = await use_case.execute(
        SetupFirstUserInput(name="Admin", email="admin@example.com")
    )
    assert output.name == "Admin"
    assert output.email == "admin@example.com"
    assert output.role == UserRole.ADMIN
    assert output.is_active is True
    assert output.slack_user_id is None

    # Verify user was actually persisted
    saved = await repo.get_by_email("admin@example.com")
    assert saved is not None
    assert saved.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_setup_first_user_raises_when_users_exist(
    repo: InMemoryUserRepository,
    use_case: SetupFirstUserUseCase,
) -> None:
    """SetupAlreadyCompleteError is raised when users already exist."""
    existing = User(
        id=UserId.generate(),
        name="Existing",
        email="existing@example.com",
        role=UserRole.MEMBER,
    )
    repo.add(existing)

    with pytest.raises(SetupAlreadyCompleteError):
        await use_case.execute(
            SetupFirstUserInput(name="New Admin", email="new@example.com")
        )
