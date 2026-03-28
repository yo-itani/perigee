"""SQLAlchemy implementation of RefreshTokenRepository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.auth.refresh_token_repository import (
    RefreshTokenRecord,
    RefreshTokenRepository,
)
from foundation.auth.tables import RefreshTokenTable


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    """SQLAlchemy-based implementation of RefreshTokenRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: RefreshTokenRecord) -> None:
        row = RefreshTokenTable(
            id=record.id,
            token_hash=record.token_hash,
            user_id=record.user_id,
            token_family_id=record.token_family_id,
            expires_at=record.expires_at,
            is_revoked=record.is_revoked,
            created_at=record.created_at,
        )
        self._session.add(row)
        await self._session.flush()

    async def find_by_token_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        stmt = select(RefreshTokenTable).where(
            RefreshTokenTable.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_record(row)

    async def revoke_by_family_id(self, family_id: str) -> None:
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.token_family_id == family_id,
                RefreshTokenTable.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def revoke_by_user_id(self, user_id: str) -> None:
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.user_id == user_id,
                RefreshTokenTable.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete_expired(self, before: datetime) -> int:
        stmt = delete(RefreshTokenTable).where(
            RefreshTokenTable.expires_at < before,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    @staticmethod
    def _to_record(row: RefreshTokenTable) -> RefreshTokenRecord:
        return RefreshTokenRecord(
            id=row.id,
            token_hash=row.token_hash,
            user_id=row.user_id,
            token_family_id=row.token_family_id,
            expires_at=row.expires_at,
            is_revoked=row.is_revoked,
            created_at=row.created_at,
        )
