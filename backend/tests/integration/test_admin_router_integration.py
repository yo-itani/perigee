"""Integration tests for admin_router (user management CRUD).

Target endpoints:
- POST /users -- create user (201, 409 duplicate email, 403 non-admin)
- GET /users -- list users with pagination
- GET /users/{user_id} -- get user detail (200, 404)
- PUT /users/{user_id} -- update user (200, 404)
- PUT /users/{user_id}/deactivate -- deactivate user (200)
- PUT /users/{user_id}/activate -- activate user (200)
- POST /users/{user_id}/invite -- create invitation token (201)

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
from foundation.auth.tables import InvitationTokenTable
from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable
from tests.helpers import auth_headers, create_test_user

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _new_admin(session_factory: async_sessionmaker[AsyncSession]) -> str:
    """Create an admin user in the DB and return its id string."""
    uid = str(uuid.uuid4())
    async with session_factory() as s:
        await create_test_user(
            s,
            user_id=UserId(uuid.UUID(uid)),
            name="Admin User",
            role="admin",
        )
        await s.commit()
    return uid


async def _new_member(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str = "Member User",
    is_active: bool = True,
) -> str:
    """Create a member user in the DB and return its id string."""
    uid = str(uuid.uuid4())
    async with session_factory() as s:
        await create_test_user(
            s,
            user_id=UserId(uuid.UUID(uid)),
            name=name,
            role="member",
            is_active=is_active,
        )
        await s.commit()
    return uid


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


# =====================================================================
# POST /users -- Create user
# =====================================================================


class TestCreateUser:
    """POST /users -- user creation by admin."""

    async def test_create_user_returns_201(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Admin can create a new user; response is 201 with correct body."""
        admin_id = await _new_admin(session_factory)
        new_email = f"new-{uuid.uuid4()}@test.local"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                "/users",
                headers=auth_headers(admin_id),
                json={
                    "name": "New User",
                    "email": new_email,
                    "role": "member",
                },
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New User"
        assert body["email"] == new_email
        assert body["role"] == "member"
        assert body["is_active"] is True
        # Validate that a UUID was assigned
        uuid.UUID(body["id"])

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(
                select(UserTable).where(UserTable.id == body["id"])
            )
            row = result.scalar_one()
            assert row.name == "New User"
            assert row.email == new_email
            assert row.role == "member"
            assert row.is_active is True

    async def test_create_user_duplicate_email_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating a user with an already-taken email returns 409."""
        admin_id = await _new_admin(session_factory)
        existing_email = f"existing-{uuid.uuid4()}@test.local"

        # Create first user with this email
        async with session_factory() as s:
            await create_test_user(s, email=existing_email)
            await s.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                "/users",
                headers=auth_headers(admin_id),
                json={
                    "name": "Duplicate Email User",
                    "email": existing_email,
                    "role": "member",
                },
            )

        assert resp.status_code == 409

    async def test_create_user_non_admin_returns_403(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Non-admin user attempting to create a user gets 403."""
        member_id = await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                "/users",
                headers=auth_headers(member_id),
                json={
                    "name": "Should Fail",
                    "email": f"fail-{uuid.uuid4()}@test.local",
                    "role": "member",
                },
            )

        assert resp.status_code == 403


# =====================================================================
# GET /users -- List users
# =====================================================================


class TestListUsers:
    """GET /users -- list users with pagination."""

    async def test_list_users_returns_200_with_all_users(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Admin can list users; response includes all created users."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get(
                "/users",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        user_ids = [u["id"] for u in body["users"]]
        assert admin_id in user_ids
        assert member_id in user_ids

    async def test_list_users_pagination(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Pagination parameters limit and offset work correctly."""
        admin_id = await _new_admin(session_factory)

        # Create a few extra users
        for _ in range(3):
            await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Request with limit=2
            resp = await client.get(
                "/users?limit=2&offset=0",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["users"]) == 2
        assert body["total"] >= 4  # admin + 3 members at minimum


# =====================================================================
# GET /users/{user_id} -- Get user detail
# =====================================================================


class TestGetUserDetail:
    """GET /users/{user_id} -- single user detail."""

    async def test_get_user_detail_returns_200(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Admin can retrieve a user's detail by ID."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get(
                f"/users/{member_id}",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == member_id
        assert body["name"] == "Member User"
        assert body["role"] == "member"
        assert body["is_active"] is True

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == member_id))
            row = result.scalar_one()
            assert body["name"] == row.name
            assert body["email"] == row.email
            assert body["role"] == row.role
            assert body["is_active"] == row.is_active

    async def test_get_user_detail_not_found_returns_404(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Requesting a non-existent user returns 404."""
        admin_id = await _new_admin(session_factory)
        non_existent_id = str(uuid.uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.get(
                f"/users/{non_existent_id}",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 404


# =====================================================================
# PUT /users/{user_id} -- Update user
# =====================================================================


class TestUpdateUser:
    """PUT /users/{user_id} -- update user details."""

    async def test_update_user_returns_200_with_updated_values(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Admin can update name, email, and role; response reflects changes."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(session_factory)
        updated_email = f"updated-{uuid.uuid4()}@test.local"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                f"/users/{member_id}",
                headers=auth_headers(admin_id),
                json={
                    "name": "Updated Name",
                    "email": updated_email,
                    "role": "admin",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Updated Name"
        assert body["email"] == updated_email
        assert body["role"] == "admin"

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == member_id))
            row = result.scalar_one()
            assert row.name == "Updated Name"
            assert row.email == updated_email
            assert row.role == "admin"

    async def test_update_user_not_found_returns_404(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Updating a non-existent user returns 404."""
        admin_id = await _new_admin(session_factory)
        non_existent_id = str(uuid.uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                f"/users/{non_existent_id}",
                headers=auth_headers(admin_id),
                json={
                    "name": "Ghost",
                    "email": f"ghost-{uuid.uuid4()}@test.local",
                    "role": "member",
                },
            )

        assert resp.status_code == 404


# =====================================================================
# PUT /users/{user_id}/deactivate
# =====================================================================


class TestDeactivateUser:
    """PUT /users/{user_id}/deactivate -- deactivate a user."""

    async def test_deactivate_user_returns_200_with_is_active_false(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Deactivating a user returns 200 with is_active=false."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                f"/users/{member_id}/deactivate",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is False

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == member_id))
            row = result.scalar_one()
            assert row.is_active is False


# =====================================================================
# PUT /users/{user_id}/activate
# =====================================================================


class TestActivateUser:
    """PUT /users/{user_id}/activate -- activate a deactivated user."""

    async def test_activate_user_returns_200_with_is_active_true(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Activating a deactivated user returns 200 with is_active=true."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(
            session_factory, name="Inactive Member", is_active=False
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                f"/users/{member_id}/activate",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is True

        # DB verification via separate session
        async with session_factory() as s:
            result = await s.execute(select(UserTable).where(UserTable.id == member_id))
            row = result.scalar_one()
            assert row.is_active is True


# =====================================================================
# POST /users/{user_id}/invite -- Create invitation
# =====================================================================


class TestCreateInvitation:
    """POST /users/{user_id}/invite -- generate invitation token."""

    async def test_create_invitation_returns_201_and_persists_token(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Admin can create an invitation; token row exists in DB."""
        admin_id = await _new_admin(session_factory)
        member_id = await _new_member(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/users/{member_id}/invite",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 201
        body = resp.json()
        assert "token" in body
        assert "expires_at" in body
        assert len(body["token"]) > 0

        # Verify invitation_tokens table has a row for this user
        # (invite endpoint commits explicitly, so data is visible from another session)
        async with session_factory() as s:
            result = await s.execute(
                select(InvitationTokenTable).where(
                    InvitationTokenTable.user_id == member_id
                )
            )
            row = result.scalar_one()
            assert row.user_id == member_id
            assert row.is_used is False

    async def test_create_invitation_for_nonexistent_user_returns_404(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating an invitation for a non-existent user returns 404."""
        admin_id = await _new_admin(session_factory)
        non_existent_id = str(uuid.uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/users/{non_existent_id}/invite",
                headers=auth_headers(admin_id),
            )

        assert resp.status_code == 404
