"""Tests for JWT-based authentication dependencies."""

import uuid
from unittest.mock import patch

from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_current_user
from foundation.auth.dependencies import parse_user_id_from_jwt
from foundation.auth.jwt_token import create_access_token
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import (
    InMemoryUserRepository,
)

_TEST_SECRET = "test-secret-key-for-unit-tests-32b"


def _make_token(user_id: str) -> str:
    """Create a valid JWT access token for testing."""
    return create_access_token(
        user_id=user_id,
        secret_key=_TEST_SECRET,
        expire_minutes=30,
    )


class _FakeSettings:
    jwt_secret_key = _TEST_SECRET


def _patch_settings():  # type: ignore[no-untyped-def]
    return patch(
        "foundation.auth.dependencies.settings", _FakeSettings()
    )


# ---------------------------------------------------------------------------
# parse_user_id_from_jwt (JWT parsing, no DB)
# ---------------------------------------------------------------------------


def _make_parse_app() -> FastAPI:
    app = FastAPI()

    @app.get("/test-parse")
    async def _ep(request: Request) -> dict[str, str]:
        result = await parse_user_id_from_jwt(request)
        return {"user_id": str(result.value)}

    return app


async def test_valid_jwt_returns_user_id() -> None:
    uid = str(uuid.uuid4())
    token = _make_token(uid)
    app = _make_parse_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get(
                "/test-parse",
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 200
    assert resp.json() == {"user_id": uid}


async def test_missing_auth_header_returns_401() -> None:
    app = _make_parse_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/test-parse")
    assert resp.status_code == 401


async def test_invalid_token_returns_401() -> None:
    app = _make_parse_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get(
                "/test-parse",
                headers={"Authorization": "Bearer bad-token"},
            )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user (with DB check via in-memory repo)
# ---------------------------------------------------------------------------

_ACTIVE_USER_ID = str(uuid.uuid4())
_INACTIVE_USER_ID = str(uuid.uuid4())
_UNKNOWN_USER_ID = str(uuid.uuid4())

_active_user = User(
    id=UserId.from_str(_ACTIVE_USER_ID),
    name="Active",
    email="active@example.com",
    role=UserRole.MEMBER,
    is_active=True,
)
_inactive_user = User(
    id=UserId.from_str(_INACTIVE_USER_ID),
    name="Inactive",
    email="inactive@example.com",
    role=UserRole.MEMBER,
    is_active=False,
)

_repo = InMemoryUserRepository(users=[_active_user, _inactive_user])


def _build_auth_app() -> FastAPI:
    from fastapi import HTTPException

    from api.dependencies import get_session

    app = FastAPI()

    @app.get("/test-auth")
    async def _auth_endpoint(
        user: User = Depends(get_current_user),  # noqa: B008
    ) -> dict[str, str]:
        return {"user_id": str(user.id.value)}

    async def _fake_session():  # type: ignore[no-untyped-def]
        yield None

    app.dependency_overrides[get_session] = _fake_session

    async def _fake_get_current_user(
        request: Request,
    ) -> User:
        parsed_id = await parse_user_id_from_jwt(request)
        user = await _repo.get_by_id(parsed_id)
        if user is None:
            raise HTTPException(
                status_code=403, detail="User not found"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is deactivated",
            )
        return user

    app.dependency_overrides[get_current_user] = (
        _fake_get_current_user
    )
    return app


def _auth_header(user_id: str) -> dict[str, str]:
    token = _make_token(user_id)
    return {"Authorization": f"Bearer {token}"}


async def test_active_user_returns_200() -> None:
    app = _build_auth_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get(
                "/test-auth",
                headers=_auth_header(_ACTIVE_USER_ID),
            )
    assert resp.status_code == 200
    assert resp.json() == {"user_id": _ACTIVE_USER_ID}


async def test_inactive_user_returns_403() -> None:
    app = _build_auth_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get(
                "/test-auth",
                headers=_auth_header(_INACTIVE_USER_ID),
            )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User account is deactivated"


async def test_unknown_user_returns_403() -> None:
    app = _build_auth_app()
    transport = ASGITransport(app=app)
    with _patch_settings():
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get(
                "/test-auth",
                headers=_auth_header(_UNKNOWN_USER_ID),
            )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User not found"
