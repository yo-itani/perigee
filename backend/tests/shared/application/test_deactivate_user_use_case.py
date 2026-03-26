"""Tests for DeactivateUserUseCase."""

from __future__ import annotations

import pytest

from shared.application.deactivate_user_use_case import (
    DeactivateUserInput,
    DeactivateUserUseCase,
    LastAdminError,
    UserNotFoundError,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def use_case(repo: InMemoryUserRepository) -> DeactivateUserUseCase:
    return DeactivateUserUseCase(user_repo=repo)


def _make_user(
    *,
    role: UserRole = UserRole.MEMBER,
    is_active: bool = True,
    email: str | None = None,
) -> User:
    uid = UserId.generate()
    return User(
        id=uid,
        name="User",
        email=email or f"{uid.value}@example.com",
        role=role,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_deactivate_member_success(
    repo: InMemoryUserRepository, use_case: DeactivateUserUseCase
) -> None:
    """A member user can be deactivated."""
    user = _make_user(role=UserRole.MEMBER)
    repo.add(user)

    output = await use_case.execute(DeactivateUserInput(user_id=user.id))
    assert output.is_active is False


@pytest.mark.asyncio
async def test_deactivate_not_found(use_case: DeactivateUserUseCase) -> None:
    """Deactivating a non-existent user raises UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await use_case.execute(DeactivateUserInput(user_id=UserId.generate()))


@pytest.mark.asyncio
async def test_deactivate_last_admin_rejected(
    repo: InMemoryUserRepository, use_case: DeactivateUserUseCase
) -> None:
    """Cannot deactivate the last active admin."""
    admin = _make_user(role=UserRole.ADMIN)
    repo.add(admin)

    with pytest.raises(LastAdminError):
        await use_case.execute(DeactivateUserInput(user_id=admin.id))


@pytest.mark.asyncio
async def test_deactivate_admin_allowed_when_multiple(
    repo: InMemoryUserRepository, use_case: DeactivateUserUseCase
) -> None:
    """Deactivating an admin is allowed when there are multiple active admins."""
    admin1 = _make_user(role=UserRole.ADMIN, email="a1@example.com")
    admin2 = _make_user(role=UserRole.ADMIN, email="a2@example.com")
    repo.add(admin1)
    repo.add(admin2)

    output = await use_case.execute(DeactivateUserInput(user_id=admin1.id))
    assert output.is_active is False
