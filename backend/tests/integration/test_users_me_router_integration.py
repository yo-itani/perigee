"""Integration tests for users/me endpoints (profile get & update).

Target endpoints:
- GET  /users/me  -- authenticated user profile retrieval
- PUT  /users/me  -- authenticated user profile update (name, email)

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable
from tests.helpers import auth_headers, create_test_user

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_app():
    """Create a FastAPI app wired with routers and exception handlers."""
    from fastapi import FastAPI

    app = FastAPI()
    app.state.event_dispatcher = create_event_dispatcher()
    register_exception_handlers(app)
    register_routers(app)
    return app


@pytest.fixture
def app():
    return _create_test_app()


async def _new_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str = "Test User",
    email: str | None = None,
    role: str = "member",
    slack_user_id: str | None = None,
) -> str:
    """Create a new random user in the DB and return its id string."""
    uid = str(uuid.uuid4())
    async with session_factory() as s:
        await create_test_user(
            s,
            user_id=UserId(uuid.UUID(uid)),
            name=name,
            email=email or f"{uid}@test.local",
            role=role,
        )
        # Set slack_user_id directly if provided (create_test_user doesn't support it)
        if slack_user_id is not None:
            result = await s.execute(select(UserTable).where(UserTable.id == uid))
            row = result.scalar_one()
            row.slack_user_id = slack_user_id
            await s.flush()
        await s.commit()
    return uid


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


class TestGetMyProfile:
    """Tests for GET /users/me."""

    async def test_returns_profile_for_authenticated_user(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Authenticated request returns 200 with profile matching DB."""
        user_id = await _new_user(
            session_factory,
            name="Alice Smith",
            email="alice@example.com",
            role="member",
            slack_user_id="U12345",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get("/users/me", headers=auth_headers(user_id))

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id
        assert data["name"] == "Alice Smith"
        assert data["email"] == "alice@example.com"
        assert data["role"] == "member"
        assert data["is_active"] is True
        assert data["slack_user_id"] == "U12345"

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == user_id))
            row = result.scalar_one()
            assert data["name"] == row.name
            assert data["email"] == row.email
            assert data["role"] == row.role
            assert data["is_active"] == row.is_active
            assert data["slack_user_id"] == row.slack_user_id

    async def test_returns_401_without_token(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Request without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get("/users/me")

        assert resp.status_code == 401

    async def test_returns_401_with_invalid_token(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Request with an invalid JWT returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get(
                "/users/me",
                headers={"Authorization": "Bearer invalid-token-string"},
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/me
# ---------------------------------------------------------------------------


class TestUpdateMyProfile:
    """Tests for PUT /users/me."""

    async def test_update_name_and_email(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """PUT updates name and email, response reflects new values."""
        user_id = await _new_user(
            session_factory,
            name="Original Name",
            email="original@example.com",
            role="member",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(user_id),
                json={"name": "Updated Name", "email": "updated@example.com"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@example.com"

        # Verify DB was actually updated via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == user_id))
            row = result.scalar_one()
            assert row.name == "Updated Name"
            assert row.email == "updated@example.com"

    async def test_role_is_not_changed_by_update(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """PUT /users/me does not change the user's role."""
        user_id = await _new_user(
            session_factory,
            name="Role User",
            email="role@example.com",
            role="admin",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(user_id),
                json={"name": "New Name", "email": "newemail@example.com"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"

        # Verify role unchanged in DB
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == user_id))
            row = result.scalar_one()
            assert row.role == "admin"

    async def test_get_reflects_update(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """After PUT, a subsequent GET returns the updated profile."""
        user_id = await _new_user(
            session_factory,
            name="Before Update",
            email="before@example.com",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Update
            put_resp = await client.put(
                "/users/me",
                headers=auth_headers(user_id),
                json={"name": "After Update", "email": "after@example.com"},
            )
            assert put_resp.status_code == 200

            # GET should reflect the update
            get_resp = await client.get("/users/me", headers=auth_headers(user_id))

        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["name"] == "After Update"
        assert data["email"] == "after@example.com"

    async def test_returns_401_without_token(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """PUT without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                "/users/me",
                json={"name": "Hacker", "email": "hacker@example.com"},
            )

        assert resp.status_code == 401

    async def test_duplicate_email_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """PUT with an email already taken by another user returns 409."""
        # Create two users
        _user_a_id = await _new_user(
            session_factory,
            name="User A",
            email="taken@example.com",
        )
        user_b_id = await _new_user(
            session_factory,
            name="User B",
            email="userb@example.com",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(user_b_id),
                json={"name": "User B", "email": "taken@example.com"},
            )

        assert resp.status_code == 409

    async def test_invalid_email_returns_422(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """PUT with malformed email returns 422 (validation error)."""
        user_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                "/users/me",
                headers=auth_headers(user_id),
                json={"name": "Name", "email": "not-an-email"},
            )

        assert resp.status_code == 422
