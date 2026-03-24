from __future__ import annotations

import uuid

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId, RecordStatus
from contexts.record.infrastructure.tables import (
    RecordConfirmedAgendaTable,
    RecordTable,
    RecordViewerTable,
)
from shared.domain.value_objects import UserId


class SqlAlchemyRecordRepository(RecordRepository):
    """SQLAlchemy-based implementation of RecordRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: RecordId) -> Record | None:
        stmt = select(RecordTable).where(RecordTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: Record) -> None:
        existing = await self._session.get(RecordTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    async def exists_by_participant(
        self, user_id: UserId, counterpart_id: UserId
    ) -> bool:
        stmt = select(
            exists().where(
                RecordTable.counterpart_id == str(counterpart_id.value),
                or_(
                    RecordTable.organizer_id == str(user_id.value),
                    RecordTable.counterpart_id == str(user_id.value),
                ),
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def list_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
        offset: int,
        limit: int,
    ) -> list[Record]:
        stmt = self._visible_published_by_pair_stmt(
            actor_id, organizer_id, counterpart_id
        )
        stmt = (
            stmt.order_by(
                RecordTable.conducted_at.desc(),
                RecordTable.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.unique().scalars().all()]

    async def count_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> int:
        from sqlalchemy import func

        base = self._visible_published_by_pair_stmt(
            actor_id, organizer_id, counterpart_id
        ).with_only_columns(func.count(RecordTable.id))
        result = await self._session.execute(base)
        return int(result.scalar() or 0)

    async def get_latest_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> Record | None:
        records = await self.list_visible_published_by_pair(
            actor_id, organizer_id, counterpart_id, offset=0, limit=1
        )
        return records[0] if records else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _visible_published_by_pair_stmt(
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> select:  # type: ignore[type-arg]
        """Build base SELECT for published records visible to actor."""
        actor_str = str(actor_id.value)
        return (
            select(RecordTable)
            .outerjoin(
                RecordViewerTable,
                RecordTable.id == RecordViewerTable.record_id,
            )
            .where(
                RecordTable.organizer_id == str(organizer_id.value),
                RecordTable.counterpart_id == str(counterpart_id.value),
                RecordTable.status == RecordStatus.PUBLISHED.value,
                or_(
                    RecordTable.organizer_id == actor_str,
                    RecordTable.counterpart_id == actor_str,
                    RecordViewerTable.user_id == actor_str,
                ),
            )
        )

    async def _insert(self, entity: Record) -> None:
        record_row = RecordTable(
            id=str(entity.id.value),
            organizer_id=str(entity.organizer_id.value),
            counterpart_id=str(entity.counterpart_id.value),
            schedule_id=(str(entity.schedule_id.value) if entity.schedule_id else None),
            memo=entity.memo.value,
            status=entity.status.value,
            conducted_at=entity.conducted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        for viewer_id in entity.viewers:
            viewer_row = RecordViewerTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                user_id=str(viewer_id.value),
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            record_row.viewers.append(viewer_row)
        for agenda_id in entity.confirmed_agenda_ids:
            agenda_row = RecordConfirmedAgendaTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                agenda_id=str(agenda_id.value),
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            record_row.confirmed_agendas.append(agenda_row)
        self._session.add(record_row)
        await self._session.flush()

    async def _update(self, entity: Record, existing: RecordTable) -> None:
        # Update scalar fields
        existing.memo = entity.memo.value
        existing.status = entity.status.value
        existing.conducted_at = entity.conducted_at
        existing.schedule_id = (
            str(entity.schedule_id.value) if entity.schedule_id else None
        )
        existing.updated_at = entity.updated_at

        # Replace viewers: delete all, then re-insert
        existing.viewers.clear()
        await self._session.flush()

        for viewer_id in entity.viewers:
            new_viewer = RecordViewerTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                user_id=str(viewer_id.value),
                created_at=entity.updated_at,
                updated_at=entity.updated_at,
            )
            existing.viewers.append(new_viewer)

        # Replace confirmed agendas: delete all, then re-insert
        existing.confirmed_agendas.clear()
        await self._session.flush()

        for agenda_id in entity.confirmed_agenda_ids:
            new_agenda = RecordConfirmedAgendaTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                agenda_id=str(agenda_id.value),
                created_at=entity.updated_at,
                updated_at=entity.updated_at,
            )
            existing.confirmed_agendas.append(new_agenda)

        await self._session.flush()

    @staticmethod
    def _to_entity(row: RecordTable) -> Record:
        viewers = [UserId.from_str(v.user_id) for v in row.viewers]
        confirmed_agenda_ids = {
            AgendaId.from_str(a.agenda_id) for a in row.confirmed_agendas
        }
        return Record(
            id=RecordId.from_str(row.id),
            organizer_id=UserId.from_str(row.organizer_id),
            counterpart_id=UserId.from_str(row.counterpart_id),
            schedule_id=(
                ScheduleId.from_str(row.schedule_id) if row.schedule_id else None
            ),
            _memo=Memo(row.memo),
            _status=RecordStatus(row.status),
            _viewers=viewers,
            _confirmed_agenda_ids=confirmed_agenda_ids,
            conducted_at=row.conducted_at,
            created_at=row.created_at,
            _updated_at=row.updated_at,
        )
