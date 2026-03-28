"""SQLAlchemy implementation of LoginAttemptRepository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.auth.login_attempt_repository import (
    LoginAttemptRecord,
    LoginAttemptRepository,
)
from foundation.auth.tables import LoginAttemptTable


class SqlAlchemyLoginAttemptRepository(LoginAttemptRepository):
    """SQLAlchemy-based implementation of LoginAttemptRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: LoginAttemptRecord) -> None:
        row = LoginAttemptTable(
            id=record.id,
            email=record.email,
            ip_address=record.ip_address,
            attempted_at=record.attempted_at,
            is_success=record.is_success,
        )
        self._session.add(row)
        await self._session.flush()

    async def count_recent_failures(
        self, email: str, since: datetime
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(LoginAttemptTable)
            .where(
                LoginAttemptTable.email == email,
                LoginAttemptTable.attempted_at >= since,
                LoginAttemptTable.is_success.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_older_than(self, before: datetime) -> int:
        stmt = delete(LoginAttemptTable).where(
            LoginAttemptTable.attempted_at < before,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]
