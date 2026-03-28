"""Tests for SetPasswordUseCase."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from foundation.auth.in_memory_invitation_token_repository import (
    InMemoryInvitationTokenRepository,
)
from foundation.auth.in_memory_refresh_token_repository import (
    InMemoryRefreshTokenRepository,
)
from foundation.auth.invitation_token_repository import InvitationTokenRecord
from foundation.auth.password import verify_password
from foundation.auth.refresh_token_repository import RefreshTokenRecord
from foundation.auth.token_hash import generate_token, hash_token
from foundation.auth.use_cases.set_password_use_case import (
    InvalidInvitationTokenError,
    SetPasswordInput,
    SetPasswordUseCase,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


def _make_user(user_id: UserId | None = None) -> User:
    return User(
        id=user_id or UserId.generate(),
        name="Test User",
        email="user@example.com",
        role=UserRole.MEMBER,
    )


def _make_invitation_record(
    user_id: str,
    raw_token: str,
    *,
    is_used: bool = False,
    expires_at: datetime | None = None,
) -> InvitationTokenRecord:
    return InvitationTokenRecord(
        id=str(uuid.uuid4()),
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=expires_at or (datetime.now(UTC) + timedelta(hours=72)),
        is_used=is_used,
        created_at=datetime.now(UTC),
    )


def _make_use_case(
    user_repo: InMemoryUserRepository,
    invitation_repo: InMemoryInvitationTokenRepository,
    refresh_repo: InMemoryRefreshTokenRepository | None = None,
) -> SetPasswordUseCase:
    return SetPasswordUseCase(
        user_repo=user_repo,
        invitation_token_repo=invitation_repo,
        refresh_token_repo=refresh_repo or InMemoryRefreshTokenRepository(),
    )


class TestSetPasswordSuccess:
    """Tests for successful password setting."""

    async def test_sets_password_hash(self) -> None:
        """Password is hashed and saved to the user."""
        user = _make_user()
        raw_token = generate_token()
        invitation = _make_invitation_record(str(user.id.value), raw_token)

        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        use_case = _make_use_case(user_repo, invitation_repo)
        output = await use_case.execute(
            SetPasswordInput(token=raw_token, password="new-password-123")
        )

        assert output.user_id == str(user.id.value)

        # Verify password was set
        saved_user = await user_repo.get_by_id(user.id)
        assert saved_user is not None
        assert saved_user.has_password is True
        assert verify_password("new-password-123", saved_user.password_hash)  # type: ignore[arg-type]

    async def test_marks_invitation_as_used(self) -> None:
        """Invitation token is marked as used after password is set."""
        user = _make_user()
        raw_token = generate_token()
        invitation = _make_invitation_record(str(user.id.value), raw_token)

        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        use_case = _make_use_case(user_repo, invitation_repo)
        await use_case.execute(
            SetPasswordInput(token=raw_token, password="new-password-123")
        )

        found = await invitation_repo.find_by_token_hash(hash_token(raw_token))
        assert found is not None
        assert found.is_used is True

    async def test_revokes_existing_refresh_tokens(self) -> None:
        """All refresh tokens for the user are revoked when password is set."""
        user = _make_user()
        raw_token = generate_token()
        invitation = _make_invitation_record(str(user.id.value), raw_token)

        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        # Create existing refresh token
        refresh_repo = InMemoryRefreshTokenRepository()
        existing_refresh = RefreshTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=hash_token("old-refresh"),
            user_id=str(user.id.value),
            token_family_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_revoked=False,
            created_at=datetime.now(UTC),
        )
        await refresh_repo.save(existing_refresh)

        use_case = _make_use_case(user_repo, invitation_repo, refresh_repo)
        await use_case.execute(
            SetPasswordInput(token=raw_token, password="new-password-123")
        )

        # Verify refresh token was revoked
        found = await refresh_repo.find_by_token_hash(hash_token("old-refresh"))
        assert found is not None
        assert found.is_revoked is True


class TestSetPasswordFailure:
    """Tests for set-password failures."""

    async def test_unknown_token_raises(self) -> None:
        """Unknown invitation token raises InvalidInvitationTokenError."""
        user_repo = InMemoryUserRepository()
        invitation_repo = InMemoryInvitationTokenRepository()
        use_case = _make_use_case(user_repo, invitation_repo)

        with pytest.raises(InvalidInvitationTokenError, match="not found"):
            await use_case.execute(
                SetPasswordInput(token="nonexistent", password="password123")
            )

    async def test_used_token_raises(self) -> None:
        """Already-used invitation token raises InvalidInvitationTokenError."""
        user = _make_user()
        raw_token = generate_token()
        invitation = _make_invitation_record(
            str(user.id.value), raw_token, is_used=True
        )

        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        use_case = _make_use_case(user_repo, invitation_repo)

        with pytest.raises(InvalidInvitationTokenError, match="already been used"):
            await use_case.execute(
                SetPasswordInput(token=raw_token, password="password123")
            )

    async def test_expired_token_raises(self) -> None:
        """Expired invitation token raises InvalidInvitationTokenError."""
        user = _make_user()
        raw_token = generate_token()
        invitation = _make_invitation_record(
            str(user.id.value),
            raw_token,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        use_case = _make_use_case(user_repo, invitation_repo)

        with pytest.raises(InvalidInvitationTokenError, match="expired"):
            await use_case.execute(
                SetPasswordInput(token=raw_token, password="password123")
            )

    async def test_user_not_found_raises(self) -> None:
        """Token for nonexistent user raises InvalidInvitationTokenError."""
        raw_token = generate_token()
        invitation = _make_invitation_record(str(uuid.uuid4()), raw_token)

        user_repo = InMemoryUserRepository()
        invitation_repo = InMemoryInvitationTokenRepository()
        await invitation_repo.save(invitation)

        use_case = _make_use_case(user_repo, invitation_repo)

        with pytest.raises(InvalidInvitationTokenError, match="User not found"):
            await use_case.execute(
                SetPasswordInput(token=raw_token, password="password123")
            )
