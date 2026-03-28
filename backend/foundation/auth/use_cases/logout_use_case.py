"""Use case: log out by revoking the refresh token family."""

from __future__ import annotations

from foundation.auth.refresh_token_repository import RefreshTokenRepository
from foundation.auth.token_hash import hash_token


class LogoutUseCase:
    """Revoke the refresh token family for the given token."""

    def __init__(self, refresh_token_repo: RefreshTokenRepository) -> None:
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, raw_refresh_token: str) -> None:
        token_h = hash_token(raw_refresh_token)
        record = await self._refresh_token_repo.find_by_token_hash(token_h)
        if record is not None:
            await self._refresh_token_repo.revoke_by_family_id(
                record.token_family_id
            )
