from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import (
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
from contexts.preparation.infrastructure.tables import (
    ScheduleGroupAgendaTemplateTable,
    ScheduleGroupTable,
    ScheduleTable,
)
from foundation.datetime_utils import to_aware_utc, to_naive_utc
from shared.domain.value_objects import UserId


class SqlAlchemyScheduleGroupRepository(ScheduleGroupRepository):
    """SQLAlchemy-based implementation of ScheduleGroupRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: ScheduleGroupId) -> ScheduleGroup | None:
        stmt = select(ScheduleGroupTable).where(
            ScheduleGroupTable.id == str(entity_id.value)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        # Restore schedule_ids from the schedules table
        schedule_ids = await self._load_schedule_ids(entity_id)

        return self._to_entity(row, schedule_ids)

    async def save(self, entity: ScheduleGroup) -> None:
        existing = await self._session.get(ScheduleGroupTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_schedule_ids(self, group_id: ScheduleGroupId) -> list[ScheduleId]:
        """Load schedule IDs belonging to this group.

        Ordered by created_at ASC, id ASC.
        """
        stmt = (
            select(ScheduleTable.id)
            .where(ScheduleTable.schedule_group_id == str(group_id.value))
            .order_by(ScheduleTable.created_at.asc(), ScheduleTable.id.asc())
        )
        result = await self._session.execute(stmt)
        return [ScheduleId.from_str(row[0]) for row in result.fetchall()]

    async def _insert(self, entity: ScheduleGroup) -> None:
        created_naive = to_naive_utc(entity.created_at)
        group_row = ScheduleGroupTable(
            id=str(entity.id.value),
            organizer_id=str(entity.organizer_id.value),
            template_id=(str(entity.template_id.value) if entity.template_id else None),
            title=entity.title.value,
            created_at=created_naive,
            updated_at=to_naive_utc(entity.updated_at),
        )
        for position, at in enumerate(entity.agenda_templates):
            at_row = ScheduleGroupAgendaTemplateTable(
                id=str(uuid.uuid4()),
                schedule_group_id=str(entity.id.value),
                topic=at.topic.value,
                position=position,
                created_at=created_naive,
                updated_at=created_naive,
            )
            group_row.agenda_templates.append(at_row)
        self._session.add(group_row)
        await self._session.flush()

    async def _update(
        self, entity: ScheduleGroup, existing: ScheduleGroupTable
    ) -> None:
        now_naive = to_naive_utc(datetime.now(UTC))

        existing.organizer_id = str(entity.organizer_id.value)
        existing.template_id = (
            str(entity.template_id.value) if entity.template_id else None
        )
        existing.title = entity.title.value
        existing.updated_at = now_naive

        # AgendaTemplates: full delete + re-insert
        # (position-ordered list, IDs have no meaning)
        existing.agenda_templates.clear()
        await self._session.flush()

        for position, at in enumerate(entity.agenda_templates):
            new_row = ScheduleGroupAgendaTemplateTable(
                id=str(uuid.uuid4()),
                schedule_group_id=str(entity.id.value),
                topic=at.topic.value,
                position=position,
                created_at=now_naive,
                updated_at=now_naive,
            )
            existing.agenda_templates.append(new_row)

        await self._session.flush()

    @staticmethod
    def _to_entity(
        row: ScheduleGroupTable, schedule_ids: list[ScheduleId]
    ) -> ScheduleGroup:
        sorted_ats = sorted(row.agenda_templates, key=lambda x: x.position)
        agenda_templates = [AgendaTemplate(at.topic) for at in sorted_ats]

        return ScheduleGroup(
            id=ScheduleGroupId.from_str(row.id),
            organizer_id=UserId.from_str(row.organizer_id),
            template_id=(
                TemplateId.from_str(row.template_id) if row.template_id else None
            ),
            _title=ScheduleTitle(row.title),
            _agenda_templates=agenda_templates,
            _schedule_ids=schedule_ids,
            created_at=to_aware_utc(row.created_at),
            _updated_at=to_aware_utc(row.updated_at),
        )
