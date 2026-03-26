"""Tests for get_current_user and require_admin dependencies."""

import uuid

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from httpx import ASGITransport, AsyncClient

from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole

# ---------------------------------------------------------------------------
# Test fixtures: build a mini FastAPI app with in-memory user lookup
# ---------------------------------------------------------------------------

_ADMIN_ID = str(uuid.uuid4())
_MEMBER_ID = str(uuid.uuid4())
_INACTIVE_ID = str(uuid.uuid4())

_USERS: dict[str, User] = {
    _ADMIN_ID: User(
        id=UserId.from_str(_ADMIN_ID),
        name="Admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    ),
    _MEMBER_ID: User(
        id=UserId.from_str(_MEMBER_ID),
        name="Member",
        email="member@example.com",
        role=UserRole.MEMBER,
        is_active=True,
    ),
    _INACTIVE_ID: User(
        id=UserId.from_str(_INACTIVE_ID),
        name="Inactive",
        email="inactive@example.com",
        role=UserRole.ADMIN,
        is_active=False,
    ),
}

_MISSING_HEADER_DETAIL = "X-User-Id header is missing or invalid"


def _build_test_app() -> FastAPI:
    """Build a test app with in-memory user lookup."""
    app = FastAPI()

    async def fake_get_current_user(
        x_user_id: str | None = Header(default=None),
    ) -> User:
        if x_user_id is None:
            raise HTTPException(
                status_code=401,
                detail=_MISSING_HEADER_DETAIL,
            )
        user = _USERS.get(x_user_id)
        if user is None:
            raise HTTPException(status_code=403, detail="User not found")
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is deactivated",
            )
        return user

    async def fake_require_admin(
        current_user: User = Depends(fake_get_current_user),  # noqa: B008
    ) -> User:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return current_user

    @app.get("/auth-only")
    async def auth_only(
        user: User = Depends(fake_get_current_user),  # noqa: B008
    ) -> dict[str, str]:
        return {
            "user_id": str(user.id.value),
            "role": user.role.value,
        }

    @app.get("/admin-only")
    async def admin_only(
        user: User = Depends(fake_require_admin),  # noqa: B008
    ) -> dict[str, str]:
        return {
            "user_id": str(user.id.value),
            "role": user.role.value,
        }

    return app


_test_app = _build_test_app()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=_test_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests for get_current_user (auth-only endpoint)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_admin_user_is_allowed(self) -> None:
        async with await _client() as client:
            resp = await client.get("/auth-only", headers={"X-User-Id": _ADMIN_ID})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == _ADMIN_ID

    @pytest.mark.asyncio
    async def test_member_user_is_allowed(self) -> None:
        async with await _client() as client:
            resp = await client.get("/auth-only", headers={"X-User-Id": _MEMBER_ID})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == _MEMBER_ID

    @pytest.mark.asyncio
    async def test_missing_header_returns_401(self) -> None:
        async with await _client() as client:
            resp = await client.get("/auth-only")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_user_returns_403(self) -> None:
        async with await _client() as client:
            resp = await client.get(
                "/auth-only",
                headers={"X-User-Id": str(uuid.uuid4())},
            )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_inactive_user_returns_403(self) -> None:
        async with await _client() as client:
            resp = await client.get(
                "/auth-only",
                headers={"X-User-Id": _INACTIVE_ID},
            )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User account is deactivated"


# ---------------------------------------------------------------------------
# Tests for require_admin
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_admin_is_allowed(self) -> None:
        async with await _client() as client:
            resp = await client.get("/admin-only", headers={"X-User-Id": _ADMIN_ID})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_member_is_rejected(self) -> None:
        async with await _client() as client:
            resp = await client.get("/admin-only", headers={"X-User-Id": _MEMBER_ID})
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin access required"

    @pytest.mark.asyncio
    async def test_unauthenticated_is_rejected(self) -> None:
        async with await _client() as client:
            resp = await client.get("/admin-only")
        assert resp.status_code == 401
