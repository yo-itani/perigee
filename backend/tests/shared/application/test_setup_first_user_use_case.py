"""Tests for SetupFirstUserUseCase."""

from __future__ import annotations

from types import TracebackType

import pytest

from foundation.application.unit_of_work import UnitOfWork
from shared.application.setup_first_user_use_case import (
    SetupAlreadyCompleteError,
    SetupFirstUserInput,
    SetupFirstUserUseCase,
)
from shared.domain.system_settings import SystemSettings
from shared.domain.value_objects import UserRole
from shared.infrastructure.in_memory_system_settings_repository import (
    InMemorySystemSettingsRepository,
)
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


class FakeUnitOfWork(UnitOfWork):
    """Fake UnitOfWork that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def system_settings_repo() -> InMemorySystemSettingsRepository:
    return InMemorySystemSettingsRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    user_repo: InMemoryUserRepository,
    system_settings_repo: InMemorySystemSettingsRepository,
    uow: FakeUnitOfWork,
) -> SetupFirstUserUseCase:
    return SetupFirstUserUseCase(
        user_repo=user_repo,
        system_settings_repo=system_settings_repo,
        uow=uow,
    )


@pytest.mark.asyncio
async def test_setup_first_user_success(
    use_case: SetupFirstUserUseCase,
    user_repo: InMemoryUserRepository,
    system_settings_repo: InMemorySystemSettingsRepository,
    uow: FakeUnitOfWork,
) -> None:
    """The first user is created with admin role when setup is not complete."""
    output = await use_case.execute(
        SetupFirstUserInput(name="Admin", email="admin@example.com")
    )
    assert output.name == "Admin"
    assert output.email == "admin@example.com"
    assert output.role == UserRole.ADMIN
    assert output.is_active is True
    assert output.slack_user_id is None

    # Verify user was actually persisted
    saved = await user_repo.get_by_email("admin@example.com")
    assert saved is not None
    assert saved.role == UserRole.ADMIN

    # Verify system settings were marked as complete
    settings = await system_settings_repo.get()
    assert settings.is_setup_complete is True
    assert settings.setup_completed_at is not None

    # Verify UoW was committed
    assert uow.committed is True


@pytest.mark.asyncio
async def test_setup_first_user_raises_when_already_complete(
    system_settings_repo: InMemorySystemSettingsRepository,
    use_case: SetupFirstUserUseCase,
    uow: FakeUnitOfWork,
) -> None:
    """SetupAlreadyCompleteError is raised when setup is already complete."""
    from datetime import UTC, datetime

    # Mark setup as already complete
    settings = SystemSettings()
    settings.mark_setup_complete(datetime.now(UTC))
    await system_settings_repo.save(settings)

    with pytest.raises(SetupAlreadyCompleteError):
        await use_case.execute(
            SetupFirstUserInput(name="New Admin", email="new@example.com")
        )

    # Verify UoW was NOT committed (rolled back via __aexit__)
    assert uow.committed is False
    assert uow.rolled_back is True


@pytest.mark.asyncio
async def test_setup_with_password_stores_hash(
    use_case: SetupFirstUserUseCase,
    user_repo: InMemoryUserRepository,
) -> None:
    """Password is hashed and stored when provided."""
    output = await use_case.execute(
        SetupFirstUserInput(
            name="Admin",
            email="admin@example.com",
            password="secure-password-123",
        )
    )
    assert output.role == UserRole.ADMIN

    saved = await user_repo.get_by_email("admin@example.com")
    assert saved is not None
    assert saved.has_password is True

    from foundation.auth.password import verify_password

    assert verify_password("secure-password-123", saved.password_hash)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_setup_without_password_has_no_hash(
    use_case: SetupFirstUserUseCase,
    user_repo: InMemoryUserRepository,
) -> None:
    """When no password is provided, password_hash is None."""
    await use_case.execute(SetupFirstUserInput(name="Admin", email="admin@example.com"))

    saved = await user_repo.get_by_email("admin@example.com")
    assert saved is not None
    assert saved.has_password is False
