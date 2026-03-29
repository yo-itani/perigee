"""Tests for ActivateUserUseCase."""

from __future__ import annotations

import pytest

from shared.application.activate_user_use_case import (
    ActivateUserInput,
    ActivateUserUseCase,
    UserNotFoundError,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository
from tests.shared.application.fake_unit_of_work import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def use_case(uow: FakeUnitOfWork, repo: InMemoryUserRepository) -> ActivateUserUseCase:
    return ActivateUserUseCase(uow=uow, user_repo=repo)


@pytest.mark.asyncio
async def test_activate_user_success(
    repo: InMemoryUserRepository, use_case: ActivateUserUseCase
) -> None:
    """A deactivated user can be activated."""
    user = User(
        id=UserId.generate(),
        name="Inactive",
        email="inactive@example.com",
        role=UserRole.MEMBER,
        is_active=False,
    )
    repo.add(user)

    output = await use_case.execute(ActivateUserInput(user_id=user.id))
    assert output.is_active is True


@pytest.mark.asyncio
async def test_activate_not_found(use_case: ActivateUserUseCase) -> None:
    """Activating a non-existent user raises UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await use_case.execute(ActivateUserInput(user_id=UserId.generate()))
