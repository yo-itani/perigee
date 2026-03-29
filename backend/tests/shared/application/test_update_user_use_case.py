"""Tests for UpdateUserUseCase."""

from __future__ import annotations

import pytest

from shared.application.update_user_use_case import (
    EmailAlreadyTakenError,
    LastAdminError,
    UpdateUserInput,
    UpdateUserUseCase,
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
def use_case(uow: FakeUnitOfWork, repo: InMemoryUserRepository) -> UpdateUserUseCase:
    return UpdateUserUseCase(uow=uow, user_repo=repo)


def _make_user(
    *,
    name: str = "Test",
    email: str = "test@example.com",
    role: UserRole = UserRole.MEMBER,
    is_active: bool = True,
) -> User:
    return User(
        id=UserId.generate(),
        name=name,
        email=email,
        role=role,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_update_user_success(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """A user's name, email, and role can be updated."""
    user = _make_user(name="Old", email="old@example.com", role=UserRole.MEMBER)
    repo.add(user)

    output = await use_case.execute(
        UpdateUserInput(
            user_id=user.id,
            name="New",
            email="new@example.com",
            role=UserRole.ADMIN,
        )
    )
    assert output.name == "New"
    assert output.email == "new@example.com"
    assert output.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_update_user_not_found(use_case: UpdateUserUseCase) -> None:
    """Updating a non-existent user raises UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await use_case.execute(
            UpdateUserInput(
                user_id=UserId.generate(),
                name="X",
                email="x@example.com",
                role=UserRole.MEMBER,
            )
        )


@pytest.mark.asyncio
async def test_update_user_duplicate_email(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """Changing email to one already used raises EmailAlreadyTakenError."""
    other = _make_user(name="Other", email="other@example.com")
    target = _make_user(name="Target", email="target@example.com")
    repo.add(other)
    repo.add(target)

    with pytest.raises(EmailAlreadyTakenError):
        await use_case.execute(
            UpdateUserInput(
                user_id=target.id,
                name="Target",
                email="other@example.com",
                role=UserRole.MEMBER,
            )
        )


@pytest.mark.asyncio
async def test_update_user_same_email_ok(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """Keeping the same email does not trigger the duplicate check."""
    user = _make_user(name="Keep", email="keep@example.com")
    repo.add(user)

    output = await use_case.execute(
        UpdateUserInput(
            user_id=user.id,
            name="Updated",
            email="keep@example.com",
            role=UserRole.MEMBER,
        )
    )
    assert output.name == "Updated"


@pytest.mark.asyncio
async def test_last_admin_role_change_rejected(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """Cannot change role of the last active admin from admin to member."""
    admin = _make_user(name="Admin", email="admin@example.com", role=UserRole.ADMIN)
    repo.add(admin)

    with pytest.raises(LastAdminError):
        await use_case.execute(
            UpdateUserInput(
                user_id=admin.id,
                name="Admin",
                email="admin@example.com",
                role=UserRole.MEMBER,
            )
        )


@pytest.mark.asyncio
async def test_admin_role_change_allowed_when_multiple_admins(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """Changing admin role is allowed when there are multiple active admins."""
    admin1 = _make_user(name="Admin1", email="a1@example.com", role=UserRole.ADMIN)
    admin2 = _make_user(name="Admin2", email="a2@example.com", role=UserRole.ADMIN)
    repo.add(admin1)
    repo.add(admin2)

    output = await use_case.execute(
        UpdateUserInput(
            user_id=admin1.id,
            name="Admin1",
            email="a1@example.com",
            role=UserRole.MEMBER,
        )
    )
    assert output.role == UserRole.MEMBER


@pytest.mark.asyncio
async def test_inactive_admin_role_change_allowed(
    repo: InMemoryUserRepository, use_case: UpdateUserUseCase
) -> None:
    """Changing role of an inactive admin is allowed even if they are the last admin."""
    inactive_admin = _make_user(
        name="InactiveAdmin",
        email="inactive-admin@example.com",
        role=UserRole.ADMIN,
        is_active=False,
    )
    repo.add(inactive_admin)

    output = await use_case.execute(
        UpdateUserInput(
            user_id=inactive_admin.id,
            name="InactiveAdmin",
            email="inactive-admin@example.com",
            role=UserRole.MEMBER,
        )
    )
    assert output.role == UserRole.MEMBER
