"""Unit tests for system router endpoints using DI overrides."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import TracebackType

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.system_router import system_router
from foundation.application.unit_of_work import UnitOfWork
from shared.application.get_system_status_query_service import (
    GetSystemStatusQueryService,
)
from shared.application.setup_first_user_use_case import SetupFirstUserUseCase
from shared.domain.system_settings import SystemSettings
from shared.infrastructure.in_memory_system_settings_repository import (
    InMemorySystemSettingsRepository,
)
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository

# ---------------------------------------------------------------------------
# Fake UnitOfWork
# ---------------------------------------------------------------------------


class _FakeUnitOfWork(UnitOfWork):
    """No-op UnitOfWork for unit tests."""

    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def __aenter__(self) -> _FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(
    user_repo: InMemoryUserRepository,
    system_settings_repo: InMemorySystemSettingsRepository,
    uow: _FakeUnitOfWork,
) -> FastAPI:
    """Build a minimal FastAPI app with DI overrides for system_router."""
    from api.system_router import (
        _get_setup_first_user_use_case,
        _get_system_status_query_service,
    )

    app = FastAPI()
    app.include_router(system_router)

    app.dependency_overrides[_get_system_status_query_service] = lambda: (
        GetSystemStatusQueryService(system_settings_repo=system_settings_repo)
    )
    app.dependency_overrides[_get_setup_first_user_use_case] = lambda: (
        SetupFirstUserUseCase(
            user_repo=user_repo,
            system_settings_repo=system_settings_repo,
            uow=uow,
        )
    )

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def system_settings_repo() -> InMemorySystemSettingsRepository:
    return InMemorySystemSettingsRepository()


@pytest.fixture
def uow() -> _FakeUnitOfWork:
    return _FakeUnitOfWork()


@pytest.fixture
def app(
    user_repo: InMemoryUserRepository,
    system_settings_repo: InMemorySystemSettingsRepository,
    uow: _FakeUnitOfWork,
) -> FastAPI:
    return _build_app(user_repo, system_settings_repo, uow)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: GET /system/status
# ---------------------------------------------------------------------------


class TestGetSystemStatus:
    """Tests for GET /system/status."""

    @pytest.mark.asyncio
    async def test_returns_not_complete_when_fresh(self, client: AsyncClient) -> None:
        """GET /system/status returns is_setup_complete=false for fresh state."""
        response = await client.get("/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_setup_complete"] is False

    @pytest.mark.asyncio
    async def test_returns_complete_after_setup(
        self,
        system_settings_repo: InMemorySystemSettingsRepository,
        client: AsyncClient,
    ) -> None:
        """GET /system/status returns is_setup_complete=true after setup."""
        settings = SystemSettings()
        settings.mark_setup_complete(datetime.now(UTC))
        await system_settings_repo.save(settings)

        response = await client.get("/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_setup_complete"] is True


# ---------------------------------------------------------------------------
# Tests: POST /system/setup
# ---------------------------------------------------------------------------


class TestSetupFirstUser:
    """Tests for POST /system/setup."""

    @pytest.mark.asyncio
    async def test_setup_creates_admin_user(
        self,
        client: AsyncClient,
        user_repo: InMemoryUserRepository,
        system_settings_repo: InMemorySystemSettingsRepository,
        uow: _FakeUnitOfWork,
    ) -> None:
        """POST /system/setup creates the first admin user (201)."""
        response = await client.post(
            "/system/setup",
            json={"name": "Admin", "email": "admin@example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Admin"
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True

        # Verify user was persisted in the in-memory repo
        saved = await user_repo.get_by_email("admin@example.com")
        assert saved is not None

        # Verify system settings were marked as complete
        settings = await system_settings_repo.get()
        assert settings.is_setup_complete is True

        # Verify UoW was committed
        assert uow.committed is True

    @pytest.mark.asyncio
    async def test_setup_rejects_when_already_complete(
        self,
        system_settings_repo: InMemorySystemSettingsRepository,
        client: AsyncClient,
    ) -> None:
        """POST /system/setup returns 409 when setup is already complete."""
        # Pre-mark setup as complete
        settings = SystemSettings()
        settings.mark_setup_complete(datetime.now(UTC))
        await system_settings_repo.save(settings)

        response = await client.post(
            "/system/setup",
            json={"name": "Admin", "email": "admin@example.com"},
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_setup_with_password_stores_hash(
        self,
        client: AsyncClient,
        user_repo: InMemoryUserRepository,
    ) -> None:
        """POST /system/setup with password stores the password hash."""
        response = await client.post(
            "/system/setup",
            json={
                "name": "Admin",
                "email": "admin@example.com",
                "password": "secure-password-123",
            },
        )

        assert response.status_code == 201

        saved = await user_repo.get_by_email("admin@example.com")
        assert saved is not None
        assert saved.has_password is True

        from foundation.auth.password import verify_password

        assert verify_password("secure-password-123", saved.password_hash)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_setup_rejects_short_password(self, client: AsyncClient) -> None:
        """POST /system/setup returns 422 for password shorter than 8 chars."""
        response = await client.post(
            "/system/setup",
            json={
                "name": "Admin",
                "email": "admin@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_setup_rejects_invalid_email(self, client: AsyncClient) -> None:
        """POST /system/setup returns 422 for invalid email."""
        response = await client.post(
            "/system/setup",
            json={"name": "Admin", "email": "not-an-email"},
        )

        assert response.status_code == 422
