from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import TemplateId
from contexts.preparation.infrastructure.tables import (
    TemplateAgendaTemplateTable,
    TemplateDefaultCounterpartTable,
    TemplateTable,
)
from foundation.datetime_utils import to_aware_utc, to_naive_utc
from shared.domain.value_objects import UserId


class SqlAlchemyTemplateRepository(TemplateRepository):
    """SQLAlchemy-based implementation of TemplateRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: TemplateId) -> Template | None:
        stmt = select(TemplateTable).where(TemplateTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def list_by_organizer(self, organizer_id: UserId) -> list[Template]:
        stmt = select(TemplateTable).where(
            TemplateTable.organizer_id == str(organizer_id.value)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def save(self, entity: Template) -> None:
        existing = await self._session.get(TemplateTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _insert(self, entity: Template) -> None:
        created_naive = to_naive_utc(entity.created_at)
        template_row = TemplateTable(
            id=str(entity.id.value),
            organizer_id=str(entity.organizer_id.value),
            name=entity.name.value,
            created_at=created_naive,
            updated_at=to_naive_utc(entity.updated_at),
        )
        for position, user_id in enumerate(entity.default_counterparts):
            dc_row = TemplateDefaultCounterpartTable(
                id=str(uuid.uuid4()),
                template_id=str(entity.id.value),
                user_id=str(user_id.value),
                position=position,
                created_at=created_naive,
                updated_at=created_naive,
            )
            template_row.default_counterparts.append(dc_row)
        for position, at in enumerate(entity.agenda_templates):
            at_row = TemplateAgendaTemplateTable(
                id=str(uuid.uuid4()),
                template_id=str(entity.id.value),
                topic=at.topic.value,
                position=position,
                created_at=created_naive,
                updated_at=created_naive,
            )
            template_row.agenda_templates.append(at_row)
        self._session.add(template_row)
        await self._session.flush()

    async def _update(self, entity: Template, existing: TemplateTable) -> None:
        now_naive = to_naive_utc(datetime.now(UTC))

        existing.organizer_id = str(entity.organizer_id.value)
        existing.name = entity.name.value
        existing.updated_at = now_naive

        # DefaultCounterparts: full delete + re-insert
        existing.default_counterparts.clear()
        await self._session.flush()

        for position, user_id in enumerate(entity.default_counterparts):
            new_dc = TemplateDefaultCounterpartTable(
                id=str(uuid.uuid4()),
                template_id=str(entity.id.value),
                user_id=str(user_id.value),
                position=position,
                created_at=now_naive,
                updated_at=now_naive,
            )
            existing.default_counterparts.append(new_dc)

        # AgendaTemplates: full delete + re-insert
        existing.agenda_templates.clear()
        await self._session.flush()

        for position, at in enumerate(entity.agenda_templates):
            new_at = TemplateAgendaTemplateTable(
                id=str(uuid.uuid4()),
                template_id=str(entity.id.value),
                topic=at.topic.value,
                position=position,
                created_at=now_naive,
                updated_at=now_naive,
            )
            existing.agenda_templates.append(new_at)

        await self._session.flush()

    @staticmethod
    def _to_entity(row: TemplateTable) -> Template:
        sorted_dcs = sorted(row.default_counterparts, key=lambda x: x.position)
        default_counterparts = [UserId.from_str(dc.user_id) for dc in sorted_dcs]

        sorted_ats = sorted(row.agenda_templates, key=lambda x: x.position)
        agenda_templates = [AgendaTemplate(at.topic) for at in sorted_ats]

        return Template(
            id=TemplateId.from_str(row.id),
            organizer_id=UserId.from_str(row.organizer_id),
            _name=TemplateName(row.name),
            _default_counterparts=default_counterparts,
            _agenda_templates=agenda_templates,
            created_at=to_aware_utc(row.created_at),
            _updated_at=to_aware_utc(row.updated_at),
        )
