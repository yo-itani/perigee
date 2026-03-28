"""SQLAlchemy implementation of InvitationTokenRepository."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.auth.invitation_token_repository import (
    InvitationTokenRecord,
    InvitationTokenRepository,
)
from foundation.auth.tables import InvitationTokenTable


class SqlAlchemyInvitationTokenRepository(InvitationTokenRepository):
    """SQLAlchemy-based implementation of InvitationTokenRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: InvitationTokenRecord) -> None:
        row = InvitationTokenTable(
            id=record.id,
            token_hash=record.token_hash,
            user_id=record.user_id,
            expires_at=record.expires_at,
            is_used=record.is_used,
            created_at=record.created_at,
        )
        self._session.add(row)
        await self._session.flush()

    async def find_by_token_hash(
        self, token_hash: str
    ) -> InvitationTokenRecord | None:
        stmt = select(InvitationTokenTable).where(
            InvitationTokenTable.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_record(row)

    async def mark_as_used(self, token_id: str) -> None:
        stmt = (
            update(InvitationTokenTable)
            .where(InvitationTokenTable.id == token_id)
            .values(is_used=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    @staticmethod
    def _to_record(row: InvitationTokenTable) -> InvitationTokenRecord:
        return InvitationTokenRecord(
            id=row.id,
            token_hash=row.token_hash,
            user_id=row.user_id,
            expires_at=row.expires_at,
            is_used=row.is_used,
            created_at=row.created_at,
        )
