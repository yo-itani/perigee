"""Tests for CreateUserUseCase."""

from __future__ import annotations

import pytest

from shared.application.create_user_use_case import (
    CreateUserInput,
    CreateUserUseCase,
    EmailAlreadyTakenError,
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
def use_case(uow: FakeUnitOfWork, repo: InMemoryUserRepository) -> CreateUserUseCase:
    return CreateUserUseCase(uow=uow, user_repo=repo)


@pytest.mark.asyncio
async def test_create_user_success(use_case: CreateUserUseCase) -> None:
    """A new user is created with the given name, email, and role."""
    output = await use_case.execute(
        CreateUserInput(name="Alice", email="alice@example.com", role=UserRole.MEMBER)
    )
    assert output.name == "Alice"
    assert output.email == "alice@example.com"
    assert output.role == UserRole.MEMBER
    assert output.is_active is True
    assert output.slack_user_id is None


@pytest.mark.asyncio
async def test_create_admin_user(use_case: CreateUserUseCase) -> None:
    """A user can be created with admin role."""
    output = await use_case.execute(
        CreateUserInput(name="Boss", email="boss@example.com", role=UserRole.ADMIN)
    )
    assert output.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises(
    repo: InMemoryUserRepository, use_case: CreateUserUseCase
) -> None:
    """Creating a user with an existing email raises EmailAlreadyTakenError."""
    existing = User(
        id=UserId.generate(),
        name="Existing",
        email="taken@example.com",
        role=UserRole.MEMBER,
    )
    repo.add(existing)

    with pytest.raises(EmailAlreadyTakenError):
        await use_case.execute(
            CreateUserInput(name="New", email="taken@example.com", role=UserRole.MEMBER)
        )
