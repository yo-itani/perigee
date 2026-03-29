from __future__ import annotations

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.read_status_repository import ReadStatusRepository
from contexts.record.domain.value_objects import ReadStatusId, RecordId
from contexts.record.infrastructure.tables import ReadStatusTable
from foundation.datetime_utils import to_aware_utc, to_naive_utc
from shared.domain.value_objects import UserId


class SqlAlchemyReadStatusRepository(ReadStatusRepository):
    """SQLAlchemy-based implementation of ReadStatusRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: ReadStatusId) -> ReadStatus | None:
        stmt = select(ReadStatusTable).where(ReadStatusTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: ReadStatus) -> None:
        existing = await self._session.get(ReadStatusTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            self._update(entity, existing)
            await self._session.flush()

    async def upsert(self, entity: ReadStatus) -> None:
        stmt = mysql_insert(ReadStatusTable).values(
            id=str(entity.id.value),
            record_id=str(entity.record_id.value),
            user_id=str(entity.user_id.value),
            last_viewed_at=to_naive_utc(entity.last_viewed_at),
        )
        stmt = stmt.on_duplicate_key_update(
            last_viewed_at=stmt.inserted.last_viewed_at,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def find_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> ReadStatus | None:
        stmt = select(ReadStatusTable).where(
            and_(
                ReadStatusTable.record_id == str(record_id.value),
                ReadStatusTable.user_id == str(user_id.value),
            )
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def delete_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> None:
        stmt = delete(ReadStatusTable).where(
            and_(
                ReadStatusTable.record_id == str(record_id.value),
                ReadStatusTable.user_id == str(user_id.value),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def _insert(self, entity: ReadStatus) -> None:
        row = ReadStatusTable(
            id=str(entity.id.value),
            record_id=str(entity.record_id.value),
            user_id=str(entity.user_id.value),
            last_viewed_at=to_naive_utc(entity.last_viewed_at),
        )
        self._session.add(row)
        await self._session.flush()

    @staticmethod
    def _update(entity: ReadStatus, existing: ReadStatusTable) -> None:
        existing.last_viewed_at = to_naive_utc(entity.last_viewed_at)

    @staticmethod
    def _to_entity(row: ReadStatusTable) -> ReadStatus:
        return ReadStatus(
            id=ReadStatusId.from_str(row.id),
            record_id=RecordId.from_str(row.record_id),
            user_id=UserId.from_str(row.user_id),
            _last_viewed_at=to_aware_utc(row.last_viewed_at),
        )
