"""Unit tests for auth router endpoints using DI overrides."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.auth_router import auth_router
from api.dependencies import (
    get_invitation_token_repository,
    get_login_attempt_repository,
    get_refresh_token_repository,
    get_session,
    get_user_repository,
)
from foundation.auth.in_memory_invitation_token_repository import (
    InMemoryInvitationTokenRepository,
)
from foundation.auth.in_memory_login_attempt_repository import (
    InMemoryLoginAttemptRepository,
)
from foundation.auth.in_memory_refresh_token_repository import (
    InMemoryRefreshTokenRepository,
)
from foundation.auth.password import hash_password
from foundation.auth.refresh_token_repository import RefreshTokenRecord
from foundation.auth.token_hash import generate_token, hash_token
from foundation.auth.use_cases.create_invitation_use_case import (
    CreateInvitationInput,
    CreateInvitationUseCase,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import (
    InMemoryUserRepository,
)

_TEST_SECRET = "test-secret-key-for-unit-tests-32chars!"
_ALLOWED_ORIGINS = ["http://localhost:5173"]


class _FakeSettings:
    jwt_secret_key = _TEST_SECRET
    jwt_access_token_expire_minutes = 30
    jwt_refresh_token_expire_days = 7
    debug = True
    cors_origins_list = _ALLOWED_ORIGINS


def _patch_settings():  # type: ignore[no-untyped-def]
    return patch("api.auth_router.settings", _FakeSettings())


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------


def _build_app(
    user_repo: InMemoryUserRepository,
    refresh_repo: InMemoryRefreshTokenRepository,
    login_attempt_repo: InMemoryLoginAttemptRepository,
    invitation_repo: InMemoryInvitationTokenRepository,
) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)

    async def _noop() -> None:
        pass

    _fake_session_obj = SimpleNamespace(commit=_noop)

    async def _fake_session() -> AsyncGenerator[SimpleNamespace]:
        yield _fake_session_obj

    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_refresh_token_repository] = lambda: refresh_repo
    app.dependency_overrides[get_login_attempt_repository] = lambda: login_attempt_repo
    app.dependency_overrides[get_invitation_token_repository] = lambda: invitation_repo

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(
    *,
    email: str = "user@example.com",
    password: str = "correct-password",
    is_active: bool = True,
) -> User:
    return User(
        id=UserId.generate(),
        name="Test User",
        email=email,
        role=UserRole.MEMBER,
        is_active=is_active,
        password_hash=hash_password(password),
    )


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def refresh_repo() -> InMemoryRefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def login_attempt_repo() -> InMemoryLoginAttemptRepository:
    return InMemoryLoginAttemptRepository()


@pytest.fixture
def invitation_repo() -> InMemoryInvitationTokenRepository:
    return InMemoryInvitationTokenRepository()


@pytest.fixture
def app(
    user_repo: InMemoryUserRepository,
    refresh_repo: InMemoryRefreshTokenRepository,
    login_attempt_repo: InMemoryLoginAttemptRepository,
    invitation_repo: InMemoryInvitationTokenRepository,
) -> FastAPI:
    return _build_app(user_repo, refresh_repo, login_attempt_repo, invitation_repo)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: POST /auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for POST /auth/login."""

    async def test_successful_login_returns_token(
        self,
        user_repo: InMemoryUserRepository,
        client: AsyncClient,
    ) -> None:
        """Successful login returns access token and sets refresh cookie."""
        user = _make_user()
        user_repo.add(user)

        with _patch_settings():
            resp = await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "correct-password"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Check refresh token cookie is set
        assert "refresh_token" in resp.cookies

    async def test_wrong_password_returns_401(
        self,
        user_repo: InMemoryUserRepository,
        client: AsyncClient,
    ) -> None:
        """Wrong password returns 401."""
        user = _make_user()
        user_repo.add(user)

        with _patch_settings():
            resp = await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
            )

        assert resp.status_code == 401

    async def test_nonexistent_user_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Nonexistent email returns 401."""
        with _patch_settings():
            resp = await client.post(
                "/auth/login",
                json={"email": "noone@example.com", "password": "any"},
            )

        assert resp.status_code == 401

    async def test_invalid_email_returns_422(
        self,
        client: AsyncClient,
    ) -> None:
        """Invalid email format returns 422."""
        with _patch_settings():
            resp = await client.post(
                "/auth/login",
                json={"email": "not-an-email", "password": "any"},
            )

        assert resp.status_code == 422

    async def test_deactivated_user_returns_403(
        self,
        user_repo: InMemoryUserRepository,
        client: AsyncClient,
    ) -> None:
        """Deactivated user returns 403."""
        user = _make_user(is_active=False)
        user_repo.add(user)

        with _patch_settings():
            resp = await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "correct-password"},
            )

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: POST /auth/refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    """Tests for POST /auth/refresh."""

    async def test_successful_refresh_returns_new_token(
        self,
        user_repo: InMemoryUserRepository,
        refresh_repo: InMemoryRefreshTokenRepository,
        client: AsyncClient,
    ) -> None:
        """Successful refresh returns new access token and rotates cookie."""
        user = _make_user()
        user_repo.add(user)

        # Create a refresh token
        raw_token = generate_token()
        record = RefreshTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=hash_token(raw_token),
            user_id=str(user.id.value),
            token_family_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
            created_at=datetime.now(UTC),
        )
        await refresh_repo.save(record)

        with _patch_settings():
            resp = await client.post(
                "/auth/refresh",
                cookies={"refresh_token": raw_token},
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_missing_cookie_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Missing refresh cookie returns 401."""
        with _patch_settings():
            resp = await client.post(
                "/auth/refresh",
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 401

    async def test_missing_origin_returns_403(
        self,
        client: AsyncClient,
    ) -> None:
        """Missing Origin header returns 403 (CSRF protection)."""
        with _patch_settings():
            resp = await client.post(
                "/auth/refresh",
                cookies={"refresh_token": "some-token"},
            )

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: POST /auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    """Tests for POST /auth/logout."""

    async def test_successful_logout(
        self,
        refresh_repo: InMemoryRefreshTokenRepository,
        client: AsyncClient,
    ) -> None:
        """Logout revokes token and deletes cookie."""
        raw_token = generate_token()
        record = RefreshTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=hash_token(raw_token),
            user_id=str(uuid.uuid4()),
            token_family_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
            created_at=datetime.now(UTC),
        )
        await refresh_repo.save(record)

        with _patch_settings():
            resp = await client.post(
                "/auth/logout",
                cookies={"refresh_token": raw_token},
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 204

    async def test_logout_without_cookie_succeeds(
        self,
        client: AsyncClient,
    ) -> None:
        """Logout without a cookie still returns 204."""
        with _patch_settings():
            resp = await client.post(
                "/auth/logout",
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Tests: POST /auth/set-password
# ---------------------------------------------------------------------------


class TestSetPassword:
    """Tests for POST /auth/set-password."""

    async def test_successful_set_password(
        self,
        user_repo: InMemoryUserRepository,
        invitation_repo: InMemoryInvitationTokenRepository,
        client: AsyncClient,
    ) -> None:
        """Valid invitation token allows password setting."""
        user = User(
            id=UserId.generate(),
            name="Invited User",
            email="invited@example.com",
            role=UserRole.MEMBER,
        )
        user_repo.add(user)

        # Create invitation
        use_case = CreateInvitationUseCase(
            user_repo=user_repo,
            invitation_token_repo=invitation_repo,
        )
        output = await use_case.execute(CreateInvitationInput(user_id=user.id))

        with _patch_settings():
            resp = await client.post(
                "/auth/set-password",
                json={"token": output.token, "password": "new-password-123"},
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Password set successfully"

    async def test_invalid_token_returns_400(
        self,
        client: AsyncClient,
    ) -> None:
        """Invalid invitation token returns 400."""
        with _patch_settings():
            resp = await client.post(
                "/auth/set-password",
                json={"token": "bad-token", "password": "password123"},
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 400

    async def test_short_password_returns_422(
        self,
        client: AsyncClient,
    ) -> None:
        """Password shorter than 8 characters returns 422."""
        with _patch_settings():
            resp = await client.post(
                "/auth/set-password",
                json={"token": "any-token", "password": "short"},
                headers={"origin": "http://localhost:5173"},
            )

        assert resp.status_code == 422
