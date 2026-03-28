"""Tests for RefreshUseCase."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from foundation.auth.in_memory_refresh_token_repository import (
    InMemoryRefreshTokenRepository,
)
from foundation.auth.refresh_token_repository import RefreshTokenRecord
from foundation.auth.token_hash import generate_token, hash_token
from foundation.auth.use_cases.refresh_use_case import (
    InvalidRefreshTokenError,
    RefreshUseCase,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository

_SECRET = "test-secret-key-for-unit-tests-32chars!"
_ACCESS_EXPIRE = 30
_REFRESH_EXPIRE = 7


def _make_user(
    user_id: UserId | None = None,
    *,
    is_active: bool = True,
) -> User:
    return User(
        id=user_id or UserId.generate(),
        name="Test User",
        email="user@example.com",
        role=UserRole.MEMBER,
        is_active=is_active,
    )


def _make_refresh_record(
    user_id: str,
    raw_token: str,
    *,
    is_revoked: bool = False,
    expires_at: datetime | None = None,
    family_id: str | None = None,
) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=str(uuid.uuid4()),
        token_hash=hash_token(raw_token),
        user_id=user_id,
        token_family_id=family_id or str(uuid.uuid4()),
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=7)),
        is_revoked=is_revoked,
        created_at=datetime.now(UTC),
    )


def _make_use_case(
    user_repo: InMemoryUserRepository,
    refresh_repo: InMemoryRefreshTokenRepository,
) -> RefreshUseCase:
    return RefreshUseCase(
        user_repo=user_repo,
        refresh_token_repo=refresh_repo,
        jwt_secret_key=_SECRET,
        access_token_expire_minutes=_ACCESS_EXPIRE,
        refresh_token_expire_days=_REFRESH_EXPIRE,
    )


class TestRefreshSuccess:
    """Tests for successful token refresh."""

    async def test_returns_new_tokens(self) -> None:
        """Successful refresh returns new access and refresh tokens."""
        user = _make_user()
        raw_token = generate_token()
        record = _make_refresh_record(str(user.id.value), raw_token)

        user_repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        await refresh_repo.save(record)

        use_case = _make_use_case(user_repo, refresh_repo)
        output = await use_case.execute(raw_token)

        assert output.access_token
        assert output.refresh_token
        assert output.refresh_token != raw_token
        assert output.user_id == str(user.id.value)

    async def test_old_token_is_revoked(self) -> None:
        """The old refresh token is revoked after successful refresh."""
        user = _make_user()
        raw_token = generate_token()
        family_id = str(uuid.uuid4())
        record = _make_refresh_record(
            str(user.id.value), raw_token, family_id=family_id
        )

        user_repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        await refresh_repo.save(record)

        use_case = _make_use_case(user_repo, refresh_repo)
        await use_case.execute(raw_token)

        # The old token should be revoked
        old_record = await refresh_repo.find_by_token_hash(hash_token(raw_token))
        assert old_record is not None
        assert old_record.is_revoked is True


class TestRefreshFailure:
    """Tests for refresh failures."""

    async def test_unknown_token_raises(self) -> None:
        """Unknown refresh token raises InvalidRefreshTokenError."""
        user_repo = InMemoryUserRepository()
        refresh_repo = InMemoryRefreshTokenRepository()
        use_case = _make_use_case(user_repo, refresh_repo)

        with pytest.raises(InvalidRefreshTokenError, match="not found"):
            await use_case.execute("nonexistent-token")

    async def test_revoked_token_raises_and_invalidates_family(self) -> None:
        """Reusing a revoked token raises error and revokes entire family."""
        user = _make_user()
        family_id = str(uuid.uuid4())

        raw_old = generate_token()
        old_record = _make_refresh_record(
            str(user.id.value), raw_old, family_id=family_id, is_revoked=True
        )

        raw_new = generate_token()
        new_record = _make_refresh_record(
            str(user.id.value), raw_new, family_id=family_id
        )

        user_repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        await refresh_repo.save(old_record)
        await refresh_repo.save(new_record)

        use_case = _make_use_case(user_repo, refresh_repo)

        with pytest.raises(InvalidRefreshTokenError, match="revoked"):
            await use_case.execute(raw_old)

        # Both tokens in the family should be revoked
        found = await refresh_repo.find_by_token_hash(hash_token(raw_new))
        assert found is not None
        assert found.is_revoked is True

    async def test_expired_token_raises(self) -> None:
        """Expired refresh token raises InvalidRefreshTokenError."""
        user = _make_user()
        raw_token = generate_token()
        record = _make_refresh_record(
            str(user.id.value),
            raw_token,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        user_repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        await refresh_repo.save(record)

        use_case = _make_use_case(user_repo, refresh_repo)

        with pytest.raises(InvalidRefreshTokenError, match="expired"):
            await use_case.execute(raw_token)

    async def test_deactivated_user_raises(self) -> None:
        """Refresh for a deactivated user raises InvalidRefreshTokenError."""
        user = _make_user(is_active=False)
        raw_token = generate_token()
        record = _make_refresh_record(str(user.id.value), raw_token)

        user_repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        await refresh_repo.save(record)

        use_case = _make_use_case(user_repo, refresh_repo)

        with pytest.raises(InvalidRefreshTokenError, match="deactivated"):
            await use_case.execute(raw_token)
