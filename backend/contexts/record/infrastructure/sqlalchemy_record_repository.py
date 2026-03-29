from __future__ import annotations

import uuid

from sqlalchemy import exists, func, or_, select
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
from foundation.datetime_utils import to_aware_utc, to_aware_utc_optional, to_naive_utc
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
        id_subq = self._visible_record_ids_subquery(
            actor_id, organizer_id, counterpart_id
        )
        stmt = (
            select(RecordTable)
            .where(RecordTable.id.in_(select(id_subq.c.id)))
            .order_by(
                RecordTable.conducted_at.desc(),
                RecordTable.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> int:
        id_subq = self._visible_record_ids_subquery(
            actor_id, organizer_id, counterpart_id
        )
        stmt = select(func.count()).select_from(id_subq)
        result = await self._session.execute(stmt)
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

    async def list_drafts_by_organizer(
        self,
        organizer_id: UserId,
    ) -> list[Record]:
        stmt = (
            select(RecordTable)
            .where(
                RecordTable.organizer_id == str(organizer_id.value),
                RecordTable.status == RecordStatus.DRAFT.value,
            )
            .order_by(RecordTable.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _visible_record_ids_subquery(
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ):  # type: ignore[no-untyped-def]
        """Build a subquery returning record IDs visible to actor.

        Uses EXISTS subquery for viewer check instead of JOIN to avoid
        row duplication that breaks offset/limit and count.
        """
        actor_str = str(actor_id.value)
        viewer_exists = exists().where(
            RecordViewerTable.record_id == RecordTable.id,
            RecordViewerTable.user_id == actor_str,
        )
        return (
            select(RecordTable.id)
            .where(
                RecordTable.organizer_id == str(organizer_id.value),
                RecordTable.counterpart_id == str(counterpart_id.value),
                RecordTable.status == RecordStatus.PUBLISHED.value,
                or_(
                    RecordTable.organizer_id == actor_str,
                    RecordTable.counterpart_id == actor_str,
                    viewer_exists,
                ),
            )
            .subquery()
        )

    async def _insert(self, entity: Record) -> None:
        created_naive = to_naive_utc(entity.created_at)
        updated_naive = to_naive_utc(entity.updated_at)
        record_row = RecordTable(
            id=str(entity.id.value),
            organizer_id=str(entity.organizer_id.value),
            counterpart_id=str(entity.counterpart_id.value),
            schedule_id=(str(entity.schedule_id.value) if entity.schedule_id else None),
            memo=entity.memo.value,
            status=entity.status.value,
            conducted_at=to_naive_utc(entity.conducted_at),
            latest_activity_at=(
                to_naive_utc(entity.latest_activity_at)
                if entity.latest_activity_at
                else None
            ),
            created_at=created_naive,
            updated_at=updated_naive,
        )
        for viewer_id in entity.viewers:
            viewer_row = RecordViewerTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                user_id=str(viewer_id.value),
                created_at=created_naive,
                updated_at=updated_naive,
            )
            record_row.viewers.append(viewer_row)
        for agenda_id in entity.confirmed_agenda_ids:
            agenda_row = RecordConfirmedAgendaTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                agenda_id=str(agenda_id.value),
                created_at=created_naive,
                updated_at=updated_naive,
            )
            record_row.confirmed_agendas.append(agenda_row)
        self._session.add(record_row)
        await self._session.flush()

    async def _update(self, entity: Record, existing: RecordTable) -> None:
        updated_naive = to_naive_utc(entity.updated_at)
        # Update scalar fields
        existing.memo = entity.memo.value
        existing.status = entity.status.value
        existing.conducted_at = to_naive_utc(entity.conducted_at)
        existing.schedule_id = (
            str(entity.schedule_id.value) if entity.schedule_id else None
        )
        existing.latest_activity_at = (
            to_naive_utc(entity.latest_activity_at)
            if entity.latest_activity_at
            else None
        )
        existing.updated_at = updated_naive

        # Replace viewers: delete all, then re-insert
        existing.viewers.clear()
        await self._session.flush()

        for viewer_id in entity.viewers:
            new_viewer = RecordViewerTable(
                id=str(uuid.uuid4()),
                record_id=str(entity.id.value),
                user_id=str(viewer_id.value),
                created_at=updated_naive,
                updated_at=updated_naive,
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
                created_at=updated_naive,
                updated_at=updated_naive,
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
            conducted_at=to_aware_utc(row.conducted_at),
            created_at=to_aware_utc(row.created_at),
            _updated_at=to_aware_utc(row.updated_at),
            _latest_activity_at=to_aware_utc_optional(row.latest_activity_at),
        )
