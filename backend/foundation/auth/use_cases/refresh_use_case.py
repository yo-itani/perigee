"""Use case: refresh an access token using a refresh token."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from foundation.auth.jwt_token import create_access_token
from foundation.auth.refresh_token_repository import (
    RefreshTokenRecord,
    RefreshTokenRepository,
)
from foundation.auth.token_hash import generate_token, hash_token
from shared.domain.user_repository import UserRepository


class InvalidRefreshTokenError(Exception):
    """Raised when the refresh token is invalid, expired, or revoked."""


@dataclass(frozen=True)
class RefreshOutput:
    access_token: str
    refresh_token: str  # new raw refresh token (to be set in cookie)
    user_id: str


class RefreshUseCase:
    """Rotate a refresh token and issue a new access token.

    If a revoked token is reused, all tokens in the same family are
    invalidated (token theft detection).
    """

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        jwt_secret_key: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._jwt_secret_key = jwt_secret_key
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    async def execute(self, raw_refresh_token: str) -> RefreshOutput:
        now = datetime.now(UTC)
        token_h = hash_token(raw_refresh_token)

        record = await self._refresh_token_repo.find_by_token_hash(token_h)
        if record is None:
            raise InvalidRefreshTokenError("Refresh token not found")

        # Token theft detection: if a revoked token is reused, revoke entire family
        if record.is_revoked:
            await self._refresh_token_repo.revoke_by_family_id(record.token_family_id)
            raise InvalidRefreshTokenError("Refresh token has been revoked")

        if record.expires_at < now:
            raise InvalidRefreshTokenError("Refresh token has expired")

        # Verify user still exists and is active
        from shared.domain.value_objects import UserId

        user = await self._user_repo.get_by_id(UserId.from_str(record.user_id))
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("User not found or deactivated")

        # Revoke the current token (rotation)
        await self._refresh_token_repo.revoke_by_family_id(record.token_family_id)

        # Issue new refresh token in the same family
        new_raw_token = generate_token()
        # Use the same family for theft detection, but create a new family
        # to avoid false positives after legitimate rotation.
        # Actually, keep the same family so that if this new token gets stolen
        # and the old one reused, we can detect it.
        new_family_id = record.token_family_id
        new_record = RefreshTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=hash_token(new_raw_token),
            user_id=record.user_id,
            token_family_id=new_family_id,
            expires_at=now + timedelta(days=self._refresh_token_expire_days),
            is_revoked=False,
            created_at=now,
        )
        await self._refresh_token_repo.save(new_record)

        # Issue new access token
        access_token = create_access_token(
            user_id=record.user_id,
            secret_key=self._jwt_secret_key,
            expire_minutes=self._access_token_expire_minutes,
        )

        return RefreshOutput(
            access_token=access_token,
            refresh_token=new_raw_token,
            user_id=record.user_id,
        )
