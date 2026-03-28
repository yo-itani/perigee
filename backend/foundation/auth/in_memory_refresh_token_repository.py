"""In-memory implementation of RefreshTokenRepository for testing."""

from __future__ import annotations

from datetime import datetime

from foundation.auth.refresh_token_repository import (
    RefreshTokenRecord,
    RefreshTokenRepository,
)


class InMemoryRefreshTokenRepository(RefreshTokenRepository):
    """In-memory stub for RefreshTokenRepository."""

    def __init__(self) -> None:
        self._records: dict[str, RefreshTokenRecord] = {}

    async def save(self, record: RefreshTokenRecord) -> None:
        self._records[record.id] = record

    async def find_by_token_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        for record in self._records.values():
            if record.token_hash == token_hash:
                return record
        return None

    async def revoke_by_family_id(self, family_id: str) -> None:
        for record in self._records.values():
            if record.token_family_id == family_id:
                record.is_revoked = True

    async def revoke_by_user_id(self, user_id: str) -> None:
        for record in self._records.values():
            if record.user_id == user_id:
                record.is_revoked = True

    async def delete_expired(self, before: datetime) -> int:
        to_delete = [
            rid
            for rid, r in self._records.items()
            if r.expires_at < before and r.is_revoked
        ]
        for rid in to_delete:
            del self._records[rid]
        return len(to_delete)
