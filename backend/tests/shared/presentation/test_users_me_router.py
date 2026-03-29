"""Tests for GET /users/me and PUT /users/me endpoints."""

import uuid
from types import TracebackType
from typing import Self

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_current_user
from foundation.application.unit_of_work import UnitOfWork
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository
from shared.presentation.router import router
from tests.helpers import auth_headers


class _NoOpUnitOfWork(UnitOfWork):
    """No-op UoW for unit tests with in-memory repositories."""

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


# ---------------------------------------------------------------------------
# Setup: build a test app with in-memory dependencies
# ---------------------------------------------------------------------------

_ADMIN_ID = str(uuid.uuid4())
_MEMBER_ID = str(uuid.uuid4())
_INACTIVE_ID = str(uuid.uuid4())

_admin_user = User(
    id=UserId.from_str(_ADMIN_ID),
    name="Admin User",
    email="admin@example.com",
    role=UserRole.ADMIN,
    is_active=True,
    slack_user_id="U_ADMIN",
)

_member_user = User(
    id=UserId.from_str(_MEMBER_ID),
    name="Member User",
    email="member@example.com",
    role=UserRole.MEMBER,
    is_active=True,
)

_inactive_user = User(
    id=UserId.from_str(_INACTIVE_ID),
    name="Inactive User",
    email="inactive@example.com",
    role=UserRole.MEMBER,
    is_active=False,
)

_repo = InMemoryUserRepository(users=[_admin_user, _member_user, _inactive_user])


def _build_app() -> FastAPI:
    from fastapi import HTTPException, Request

    from foundation.auth.dependencies import parse_user_id_from_jwt
    from shared.application.update_my_profile_use_case import UpdateMyProfileUseCase
    from shared.presentation.dependencies import get_update_my_profile_use_case

    app = FastAPI()
    app.include_router(router)

    async def fake_get_current_user(request: Request) -> User:
        parsed_id = await parse_user_id_from_jwt(request)
        user = await _repo.get_by_id(parsed_id)
        if user is None:
            raise HTTPException(status_code=403, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")
        return user

    def fake_update_use_case() -> UpdateMyProfileUseCase:
        return UpdateMyProfileUseCase(user_repo=_repo, uow=_NoOpUnitOfWork())

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_update_my_profile_use_case] = fake_update_use_case

    return app


_test_app = _build_app()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=_test_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


class TestGetMyProfile:
    @pytest.mark.asyncio
    async def test_returns_admin_profile(self) -> None:
        async with await _client() as client:
            resp = await client.get("/users/me", headers=auth_headers(_ADMIN_ID))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == _ADMIN_ID
        assert data["name"] == "Admin User"
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True
        assert data["slack_user_id"] == "U_ADMIN"

    @pytest.mark.asyncio
    async def test_returns_member_profile(self) -> None:
        async with await _client() as client:
            resp = await client.get("/users/me", headers=auth_headers(_MEMBER_ID))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "member"
        assert data["slack_user_id"] is None

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        async with await _client() as client:
            resp = await client.get("/users/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/me
# ---------------------------------------------------------------------------


class TestUpdateMyProfile:
    @pytest.mark.asyncio
    async def test_update_name_and_email(self) -> None:
        async with await _client() as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(_MEMBER_ID),
                json={"name": "Updated Name", "email": "updated@example.com"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@example.com"
        # role should not change
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_update_preserves_role(self) -> None:
        async with await _client() as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(_ADMIN_ID),
                json={"name": "Admin Updated", "email": "admin-new@example.com"},
            )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        async with await _client() as client:
            resp = await client.put(
                "/users/me",
                json={"name": "X", "email": "x@example.com"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_email_returns_422(self) -> None:
        async with await _client() as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(_MEMBER_ID),
                json={"name": "Test", "email": "not-an-email"},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_with_same_email_succeeds(self) -> None:
        """User can update their profile while keeping the same email."""
        # First read the current email
        async with await _client() as client:
            get_resp = await client.get("/users/me", headers=auth_headers(_ADMIN_ID))
        current_email = get_resp.json()["email"]

        # Update name but keep the same email
        async with await _client() as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(_ADMIN_ID),
                json={"name": "Admin Same Email", "email": current_email},
            )
        assert resp.status_code == 200
        assert resp.json()["email"] == current_email
        assert resp.json()["name"] == "Admin Same Email"

    @pytest.mark.asyncio
    async def test_deactivated_user_returns_403(self) -> None:
        """Deactivated user cannot access API endpoints."""
        async with await _client() as client:
            resp = await client.get("/users/me", headers=auth_headers(_INACTIVE_ID))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User account is deactivated"
