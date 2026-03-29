"""Integration tests for auth router endpoints using real DB.

Tests cover all four auth endpoints:
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- POST /auth/set-password
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.auth.password import hash_password
from foundation.auth.tables import (
    InvitationTokenTable,
    LoginAttemptTable,
    RefreshTokenTable,
)
from foundation.auth.token_hash import generate_token, hash_token
from foundation.db.session import async_session_factory
from main import app
from shared.infrastructure.tables import UserTable

pytestmark = pytest.mark.integration

# CSRF-protected endpoints require an Origin header that matches
# the application's configured CORS origins.
_ORIGIN = "http://localhost:5173"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _insert_user(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    email: str = "auth-test@example.com",
    password: str | None = None,
    is_active: bool = True,
) -> str:
    """Insert a user row and return its id."""
    uid = user_id or str(uuid.uuid4())
    row = UserTable(
        id=uid,
        name="Auth Test User",
        email=email,
        role="member",
        is_active=is_active,
        password_hash=hash_password(password) if password else None,
    )
    session.add(row)
    await session.flush()
    return uid


async def _insert_invitation_token(
    session: AsyncSession,
    *,
    user_id: str,
    raw_token: str,
    expires_at: datetime | None = None,
    is_used: bool = False,
) -> str:
    """Insert an invitation token row and return its id."""
    token_id = str(uuid.uuid4())
    exp = expires_at or (datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24))
    row = InvitationTokenTable(
        id=token_id,
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=exp,
        is_used=is_used,
    )
    session.add(row)
    await session.flush()
    return token_id


async def _cleanup(session: AsyncSession, *, emails: list[str]) -> None:
    """Remove test data created during a test."""
    # Delete in FK-safe order: login_attempts, refresh_tokens,
    # invitation_tokens reference user_id but have no FK constraint,
    # so just delete by email or by user rows.
    for email in emails:
        # Find user id
        result = await session.execute(
            select(UserTable.id).where(UserTable.email == email)
        )
        uid = result.scalar()
        if uid is None:
            continue
        await session.execute(
            delete(RefreshTokenTable).where(RefreshTokenTable.user_id == uid)
        )
        await session.execute(
            delete(InvitationTokenTable).where(
                InvitationTokenTable.user_id == uid
            )
        )
        await session.execute(
            delete(LoginAttemptTable).where(LoginAttemptTable.email == email)
        )
        await session.execute(
            delete(UserTable).where(UserTable.id == uid)
        )
    await session.commit()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


class TestLoginIntegration:
    """Integration tests for POST /auth/login."""

    _EMAIL = "login-test@example.com"
    _PASSWORD = "correct-password-123"

    async def test_login_success_returns_200_and_records_attempt(self) -> None:
        """Correct credentials return 200 with access_token and record a
        successful login attempt in the DB."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                await _insert_user(s, email=self._EMAIL, password=self._PASSWORD)
                await s.commit()

            # Act
            resp = await client.post(
                "/auth/login",
                json={"email": self._EMAIL, "password": self._PASSWORD},
            )

            # Assert response
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Assert refresh_token cookie is set
            assert "refresh_token" in resp.cookies

            # Assert DB: login_attempts has a success record
            async with async_session_factory() as s:
                result = await s.execute(
                    select(LoginAttemptTable).where(
                        LoginAttemptTable.email == self._EMAIL,
                        LoginAttemptTable.is_success.is_(True),
                    )
                )
                attempts = result.scalars().all()
                assert len(attempts) >= 1

            # Assert DB: refresh_tokens has a record for this user
            async with async_session_factory() as s:
                result = await s.execute(
                    select(UserTable.id).where(UserTable.email == self._EMAIL)
                )
                uid = result.scalar_one()
                result = await s.execute(
                    select(RefreshTokenTable).where(
                        RefreshTokenTable.user_id == uid,
                        RefreshTokenTable.is_revoked.is_(False),
                    )
                )
                tokens = result.scalars().all()
                assert len(tokens) >= 1

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])

    async def test_login_wrong_password_returns_401_and_records_failure(
        self,
    ) -> None:
        """Wrong password returns 401 and records a failed login attempt."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                await _insert_user(s, email=self._EMAIL, password=self._PASSWORD)
                await s.commit()

            # Act
            resp = await client.post(
                "/auth/login",
                json={"email": self._EMAIL, "password": "wrong-password"},
            )

            # Assert response
            assert resp.status_code == 401

            # Assert DB: login_attempts has a failure record
            async with async_session_factory() as s:
                result = await s.execute(
                    select(LoginAttemptTable).where(
                        LoginAttemptTable.email == self._EMAIL,
                        LoginAttemptTable.is_success.is_(False),
                    )
                )
                attempts = result.scalars().all()
                assert len(attempts) >= 1

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])

    async def test_login_nonexistent_user_returns_401(self) -> None:
        """Login with a non-existent email returns 401."""
        nonexistent = "nonexistent@example.com"
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Ensure no leftover data
            async with async_session_factory() as s:
                await _cleanup(s, emails=[nonexistent])

            # Act
            resp = await client.post(
                "/auth/login",
                json={"email": nonexistent, "password": "any-password"},
            )

            # Assert
            assert resp.status_code == 401

        # Cleanup login attempts
        async with async_session_factory() as s:
            await s.execute(
                delete(LoginAttemptTable).where(
                    LoginAttemptTable.email == nonexistent
                )
            )
            await s.commit()


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


class TestRefreshIntegration:
    """Integration tests for POST /auth/refresh."""

    _EMAIL = "refresh-test@example.com"
    _PASSWORD = "refresh-password-123"

    async def test_refresh_with_valid_token_returns_200_and_rotates(
        self,
    ) -> None:
        """A valid refresh token returns 200 with a new access_token,
        saves a new refresh token, and revokes the old one."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup: create user and login to get a refresh token
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                await _insert_user(s, email=self._EMAIL, password=self._PASSWORD)
                await s.commit()

            login_resp = await client.post(
                "/auth/login",
                json={"email": self._EMAIL, "password": self._PASSWORD},
            )
            assert login_resp.status_code == 200
            old_refresh = login_resp.cookies.get("refresh_token")
            assert old_refresh is not None

            # Act: refresh with Origin header (CSRF)
            # Send cookie via header to ensure it reaches the ASGI app.
            resp = await client.post(
                "/auth/refresh",
                headers={
                    "Origin": _ORIGIN,
                    "Cookie": f"refresh_token={old_refresh}",
                },
            )

            # Assert response
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Assert new refresh cookie is set
            new_refresh = resp.cookies.get("refresh_token")
            assert new_refresh is not None
            assert new_refresh != old_refresh

            # Assert DB: old token is revoked, new token exists
            async with async_session_factory() as s:
                # The old token hash should be revoked
                old_hash = hash_token(old_refresh)
                result = await s.execute(
                    select(RefreshTokenTable).where(
                        RefreshTokenTable.token_hash == old_hash
                    )
                )
                old_row = result.scalar_one_or_none()
                assert old_row is not None
                assert old_row.is_revoked is True

                # A new active token should exist
                new_hash = hash_token(new_refresh)
                result = await s.execute(
                    select(RefreshTokenTable).where(
                        RefreshTokenTable.token_hash == new_hash
                    )
                )
                new_row = result.scalar_one_or_none()
                assert new_row is not None
                assert new_row.is_revoked is False

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])

    async def test_refresh_with_invalid_token_returns_401(self) -> None:
        """An invalid refresh token returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/refresh",
                headers={
                    "Origin": _ORIGIN,
                    "Cookie": "refresh_token=invalid-token-value",
                },
            )

            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


class TestLogoutIntegration:
    """Integration tests for POST /auth/logout."""

    _EMAIL = "logout-test@example.com"
    _PASSWORD = "logout-password-123"

    async def test_logout_revokes_refresh_token_and_returns_204(self) -> None:
        """Logout revokes the refresh token family in the DB and returns 204."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup: create user and login
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                await _insert_user(s, email=self._EMAIL, password=self._PASSWORD)
                await s.commit()

            login_resp = await client.post(
                "/auth/login",
                json={"email": self._EMAIL, "password": self._PASSWORD},
            )
            assert login_resp.status_code == 200
            refresh_token_value = login_resp.cookies.get("refresh_token")
            assert refresh_token_value is not None

            # Act: logout
            resp = await client.post(
                "/auth/logout",
                headers={
                    "Origin": _ORIGIN,
                    "Cookie": f"refresh_token={refresh_token_value}",
                },
            )

            # Assert response
            assert resp.status_code == 204

            # Assert DB: the refresh token is revoked
            async with async_session_factory() as s:
                token_h = hash_token(refresh_token_value)
                result = await s.execute(
                    select(RefreshTokenTable).where(
                        RefreshTokenTable.token_hash == token_h
                    )
                )
                row = result.scalar_one_or_none()
                assert row is not None
                assert row.is_revoked is True

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])


# ---------------------------------------------------------------------------
# POST /auth/set-password
# ---------------------------------------------------------------------------


class TestSetPasswordIntegration:
    """Integration tests for POST /auth/set-password."""

    _EMAIL = "setpw-test@example.com"
    _NEW_PASSWORD = "new-secure-password-123"

    async def test_set_password_updates_hash_and_returns_200(self) -> None:
        """Setting password via invitation token updates password_hash
        in the DB and returns 200."""
        raw_invitation = generate_token()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup: create user without password + invitation token
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                uid = await _insert_user(s, email=self._EMAIL, password=None)
                await _insert_invitation_token(
                    s, user_id=uid, raw_token=raw_invitation
                )
                await s.commit()

            # Act
            resp = await client.post(
                "/auth/set-password",
                json={
                    "token": raw_invitation,
                    "password": self._NEW_PASSWORD,
                },
                headers={"Origin": _ORIGIN},
            )

            # Assert response
            assert resp.status_code == 200

            # Assert DB: password_hash is set
            async with async_session_factory() as s:
                result = await s.execute(
                    select(UserTable.password_hash).where(
                        UserTable.email == self._EMAIL
                    )
                )
                pw_hash = result.scalar_one()
                assert pw_hash is not None
                assert pw_hash != ""

            # Assert DB: invitation token is marked as used
            async with async_session_factory() as s:
                token_h = hash_token(raw_invitation)
                result = await s.execute(
                    select(InvitationTokenTable).where(
                        InvitationTokenTable.token_hash == token_h
                    )
                )
                row = result.scalar_one()
                assert row.is_used is True

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])

    async def test_set_password_then_login_succeeds(self) -> None:
        """After setting a password, the user can login with it (E2E flow)."""
        raw_invitation = generate_token()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Setup
            async with async_session_factory() as s:
                await _cleanup(s, emails=[self._EMAIL])
                uid = await _insert_user(s, email=self._EMAIL, password=None)
                await _insert_invitation_token(
                    s, user_id=uid, raw_token=raw_invitation
                )
                await s.commit()

            # Set password
            set_resp = await client.post(
                "/auth/set-password",
                json={
                    "token": raw_invitation,
                    "password": self._NEW_PASSWORD,
                },
                headers={"Origin": _ORIGIN},
            )
            assert set_resp.status_code == 200

            # Login with the new password
            login_resp = await client.post(
                "/auth/login",
                json={
                    "email": self._EMAIL,
                    "password": self._NEW_PASSWORD,
                },
            )
            assert login_resp.status_code == 200
            assert "access_token" in login_resp.json()

        # Cleanup
        async with async_session_factory() as s:
            await _cleanup(s, emails=[self._EMAIL])
