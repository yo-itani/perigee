"""Tests for LogoutUseCase."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from foundation.auth.in_memory_refresh_token_repository import (
    InMemoryRefreshTokenRepository,
)
from foundation.auth.refresh_token_repository import RefreshTokenRecord
from foundation.auth.token_hash import generate_token, hash_token
from foundation.auth.use_cases.logout_use_case import LogoutUseCase


def _make_refresh_record(
    user_id: str,
    raw_token: str,
    *,
    family_id: str | None = None,
) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=str(uuid.uuid4()),
        token_hash=hash_token(raw_token),
        user_id=user_id,
        token_family_id=family_id or str(uuid.uuid4()),
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_revoked=False,
        created_at=datetime.now(UTC),
    )


class TestLogoutUseCase:
    """Tests for LogoutUseCase."""

    async def test_revokes_token_family(self) -> None:
        """Logout revokes the entire token family."""
        family_id = str(uuid.uuid4())
        raw_token = generate_token()
        record = _make_refresh_record("user-1", raw_token, family_id=family_id)

        # Add a second token in the same family
        raw_token2 = generate_token()
        record2 = _make_refresh_record("user-1", raw_token2, family_id=family_id)

        repo = InMemoryRefreshTokenRepository()
        await repo.save(record)
        await repo.save(record2)

        use_case = LogoutUseCase(refresh_token_repo=repo)
        await use_case.execute(raw_token)

        # Both tokens should be revoked
        r1 = await repo.find_by_token_hash(hash_token(raw_token))
        r2 = await repo.find_by_token_hash(hash_token(raw_token2))
        assert r1 is not None and r1.is_revoked is True
        assert r2 is not None and r2.is_revoked is True

    async def test_unknown_token_is_noop(self) -> None:
        """Logging out with an unknown token does nothing (no error)."""
        repo = InMemoryRefreshTokenRepository()
        use_case = LogoutUseCase(refresh_token_repo=repo)

        # Should not raise
        await use_case.execute("nonexistent-token")
