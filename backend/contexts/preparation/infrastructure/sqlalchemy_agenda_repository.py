from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.comment import Comment
from contexts.preparation.domain.comment_body import CommentBody
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import (
    AddedByTag,
    AgendaId,
    CommentId,
    ScheduleId,
)
from contexts.preparation.infrastructure.tables import (
    AgendaCommentTable,
    AgendaTable,
)
from shared.domain.value_objects import UserId


class SqlAlchemyAgendaRepository(AgendaRepository):
    """SQLAlchemy-based implementation of AgendaRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: AgendaId) -> Agenda | None:
        stmt = select(AgendaTable).where(AgendaTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: Agenda) -> None:
        existing = await self._session.get(AgendaTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    async def get_by_schedule_id(self, schedule_id: ScheduleId) -> list[Agenda]:
        stmt = select(AgendaTable).where(
            AgendaTable.schedule_id == str(schedule_id.value)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def get_by_schedule_ids(
        self, schedule_ids: list[ScheduleId]
    ) -> dict[ScheduleId, list[Agenda]]:
        if not schedule_ids:
            return {}
        id_strings = [str(sid.value) for sid in schedule_ids]
        stmt = select(AgendaTable).where(AgendaTable.schedule_id.in_(id_strings))
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        grouped: dict[ScheduleId, list[Agenda]] = {sid: [] for sid in schedule_ids}
        for row in rows:
            sid = ScheduleId.from_str(row.schedule_id)
            grouped[sid].append(self._to_entity(row))
        return grouped

    async def save_all(self, agendas: list[Agenda]) -> None:
        for agenda in agendas:
            await self.save(agenda)

    async def delete_by_ids(self, agenda_ids: list[AgendaId]) -> None:
        if not agenda_ids:
            return
        id_strings = [str(aid.value) for aid in agenda_ids]
        stmt = delete(AgendaTable).where(AgendaTable.id.in_(id_strings))
        await self._session.execute(stmt)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _insert(self, entity: Agenda) -> None:
        agenda_row = AgendaTable(
            id=str(entity.id.value),
            schedule_id=str(entity.schedule_id.value),
            topic=entity.topic.value,
            added_by=str(entity.added_by.value),
            added_by_tag=entity.added_by_tag.value,
            created_at=entity.created_at,
            updated_at=entity.created_at,
        )
        for comment in entity.comments:
            comment_row = AgendaCommentTable(
                id=str(comment.id.value),
                agenda_id=str(entity.id.value),
                author_id=str(comment.author_id.value),
                body=comment.body.value,
                created_at=comment.created_at,
                updated_at=comment.created_at,
            )
            agenda_row.comments.append(comment_row)
        self._session.add(agenda_row)
        await self._session.flush()

    async def _update(self, entity: Agenda, existing: AgendaTable) -> None:
        now = datetime.now(UTC)

        existing.schedule_id = str(entity.schedule_id.value)
        existing.topic = entity.topic.value
        existing.added_by = str(entity.added_by.value)
        existing.added_by_tag = entity.added_by_tag.value
        existing.updated_at = now

        # Reconcile comments
        existing_comment_map: dict[str, AgendaCommentTable] = {
            c.id: c for c in existing.comments
        }
        entity_comment_ids: set[str] = set()

        for comment in entity.comments:
            comment_id = str(comment.id.value)
            entity_comment_ids.add(comment_id)
            if comment_id in existing_comment_map:
                db_comment = existing_comment_map[comment_id]
                db_comment.author_id = str(comment.author_id.value)
                db_comment.body = comment.body.value
                db_comment.updated_at = now
            else:
                new_comment = AgendaCommentTable(
                    id=comment_id,
                    agenda_id=str(entity.id.value),
                    author_id=str(comment.author_id.value),
                    body=comment.body.value,
                    created_at=comment.created_at,
                    updated_at=comment.created_at,
                )
                existing.comments.append(new_comment)

        for comment_id, db_comment in existing_comment_map.items():
            if comment_id not in entity_comment_ids:
                existing.comments.remove(db_comment)

        await self._session.flush()

    @staticmethod
    def _to_entity(row: AgendaTable) -> Agenda:
        comments = [
            Comment(
                _id=CommentId.from_str(c.id),
                _agenda_id=AgendaId.from_str(c.agenda_id),
                _author_id=UserId.from_str(c.author_id),
                _body=CommentBody(c.body),
                _created_at=c.created_at,
            )
            for c in row.comments
        ]
        return Agenda(
            _id=AgendaId.from_str(row.id),
            _schedule_id=ScheduleId.from_str(row.schedule_id),
            _topic=Topic(row.topic),
            _added_by=UserId.from_str(row.added_by),
            _added_by_tag=AddedByTag(row.added_by_tag),
            _comments=comments,
            _created_at=row.created_at,
        )
