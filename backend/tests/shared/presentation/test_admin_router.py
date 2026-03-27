"""Tests for admin user management router endpoints."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_current_user, require_admin
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository
from shared.presentation.admin_router import admin_router
from shared.presentation.dependencies import (
    get_activate_user_use_case,
    get_create_user_use_case,
    get_deactivate_user_use_case,
    get_get_user_detail_query_service,
    get_list_users_query_service,
    get_update_user_use_case,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ADMIN_ID = str(uuid.uuid4())
_MEMBER_ID = str(uuid.uuid4())

_admin_user = User(
    id=UserId.from_str(_ADMIN_ID),
    name="Admin User",
    email="admin@example.com",
    role=UserRole.ADMIN,
    is_active=True,
)

_member_user = User(
    id=UserId.from_str(_MEMBER_ID),
    name="Member User",
    email="member@example.com",
    role=UserRole.MEMBER,
    is_active=True,
)


def _build_app(repo: InMemoryUserRepository) -> FastAPI:
    from fastapi import Header, HTTPException

    from shared.application.activate_user_use_case import ActivateUserUseCase
    from shared.application.create_user_use_case import CreateUserUseCase
    from shared.application.deactivate_user_use_case import DeactivateUserUseCase
    from shared.application.get_user_detail_query_service import (
        GetUserDetailQueryService,
    )
    from shared.application.list_users_query_service import ListUsersQueryService
    from shared.application.update_user_use_case import UpdateUserUseCase

    app = FastAPI()
    app.include_router(admin_router)

    async def fake_get_current_user(
        x_user_id: str | None = Header(default=None),
    ) -> User:
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="Missing auth")
        user = await repo.get_by_id(UserId.from_str(x_user_id))
        if user is None:
            raise HTTPException(status_code=403, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")
        return user

    async def fake_require_admin(
        x_user_id: str | None = Header(default=None),
    ) -> User:
        user = await fake_get_current_user(x_user_id)
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return user

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[require_admin] = fake_require_admin
    app.dependency_overrides[get_list_users_query_service] = lambda: (
        ListUsersQueryService(user_repo=repo)
    )
    app.dependency_overrides[get_create_user_use_case] = lambda: CreateUserUseCase(
        user_repo=repo
    )
    app.dependency_overrides[get_get_user_detail_query_service] = lambda: (
        GetUserDetailQueryService(user_repo=repo)
    )
    app.dependency_overrides[get_update_user_use_case] = lambda: UpdateUserUseCase(
        user_repo=repo
    )
    app.dependency_overrides[get_deactivate_user_use_case] = lambda: (
        DeactivateUserUseCase(user_repo=repo)
    )
    app.dependency_overrides[get_activate_user_use_case] = lambda: ActivateUserUseCase(
        user_repo=repo
    )

    return app


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository(users=[_admin_user, _member_user])


@pytest.fixture
def app(repo: InMemoryUserRepository) -> FastAPI:
    return _build_app(repo)


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _admin_headers() -> dict[str, str]:
    return {"X-User-Id": _ADMIN_ID}


def _member_headers() -> dict[str, str]:
    return {"X-User-Id": _MEMBER_ID}


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestAuthorization:
    @pytest.mark.asyncio
    async def test_member_cannot_list_users(self, client: AsyncClient) -> None:
        """Non-admin users receive 403 on admin endpoints."""
        resp = await client.get("/users", headers=_member_headers())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_member_cannot_create_user(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/users",
            headers=_member_headers(),
            json={"name": "X", "email": "x@example.com", "role": "member"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_member_cannot_get_user_detail(self, client: AsyncClient) -> None:
        resp = await client.get(f"/users/{_MEMBER_ID}", headers=_member_headers())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/users")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Invalid user_id (400)
# ---------------------------------------------------------------------------


class TestInvalidUserId:
    @pytest.mark.asyncio
    async def test_get_detail_invalid_uuid(self, client: AsyncClient) -> None:
        """Invalid UUID in path returns 400."""
        resp = await client.get("/users/not-a-uuid", headers=_admin_headers())
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid user ID format"

    @pytest.mark.asyncio
    async def test_update_invalid_uuid(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/users/invalid-uuid",
            headers=_admin_headers(),
            json={"name": "X", "email": "x@example.com", "role": "member"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_deactivate_invalid_uuid(self, client: AsyncClient) -> None:
        resp = await client.put("/users/bad-id/deactivate", headers=_admin_headers())
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_activate_invalid_uuid(self, client: AsyncClient) -> None:
        resp = await client.put("/users/bad-id/activate", headers=_admin_headers())
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CRUD operations (happy path)
# ---------------------------------------------------------------------------


class TestCrudOperations:
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient) -> None:
        """Admin can list all users."""
        resp = await client.get("/users", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 2

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, client: AsyncClient) -> None:
        """Pagination query params limit results."""
        resp = await client.get("/users?offset=0&limit=1", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 1

    @pytest.mark.asyncio
    async def test_list_users_invalid_limit(self, client: AsyncClient) -> None:
        """Invalid limit returns 422."""
        resp = await client.get("/users?limit=0", headers=_admin_headers())
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user(self, client: AsyncClient) -> None:
        """Admin can create a new user."""
        resp = await client.post(
            "/users",
            headers=_admin_headers(),
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "role": "member",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New User"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "member"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, client: AsyncClient) -> None:
        """Creating a user with a duplicate email returns 409."""
        resp = await client.post(
            "/users",
            headers=_admin_headers(),
            json={
                "name": "Dup",
                "email": "admin@example.com",
                "role": "member",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_user_detail(self, client: AsyncClient) -> None:
        """Admin can get a user's detail."""
        resp = await client.get(f"/users/{_MEMBER_ID}", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == _MEMBER_ID
        assert data["name"] == "Member User"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient) -> None:
        """Getting a non-existent user returns 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/users/{fake_id}", headers=_admin_headers())
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, client: AsyncClient) -> None:
        """Admin can update a user."""
        resp = await client.put(
            f"/users/{_MEMBER_ID}",
            headers=_admin_headers(),
            json={
                "name": "Updated Member",
                "email": "updated-member@example.com",
                "role": "member",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Member"
        assert data["email"] == "updated-member@example.com"

    @pytest.mark.asyncio
    async def test_deactivate_user(self, client: AsyncClient) -> None:
        """Admin can deactivate a member."""
        resp = await client.put(
            f"/users/{_MEMBER_ID}/deactivate", headers=_admin_headers()
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_activate_user(
        self, repo: InMemoryUserRepository, client: AsyncClient
    ) -> None:
        """Admin can activate a deactivated user."""
        inactive_id = str(uuid.uuid4())
        inactive = User(
            id=UserId.from_str(inactive_id),
            name="Inactive",
            email="inactive@example.com",
            role=UserRole.MEMBER,
            is_active=False,
        )
        repo.add(inactive)

        resp = await client.put(
            f"/users/{inactive_id}/activate", headers=_admin_headers()
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True


# ---------------------------------------------------------------------------
# Last admin protection (API level)
# ---------------------------------------------------------------------------


class TestLastAdminProtection:
    @pytest.mark.asyncio
    async def test_deactivate_last_admin_returns_409(self, client: AsyncClient) -> None:
        """Cannot deactivate the last active admin via API."""
        resp = await client.put(
            f"/users/{_ADMIN_ID}/deactivate", headers=_admin_headers()
        )
        assert resp.status_code == 409
        assert "last active admin" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_change_last_admin_role_returns_409(
        self, client: AsyncClient
    ) -> None:
        """Cannot change the last active admin's role via API."""
        resp = await client.put(
            f"/users/{_ADMIN_ID}",
            headers=_admin_headers(),
            json={
                "name": "Admin User",
                "email": "admin@example.com",
                "role": "member",
            },
        )
        assert resp.status_code == 409
        assert "last active admin" in resp.json()["detail"]
