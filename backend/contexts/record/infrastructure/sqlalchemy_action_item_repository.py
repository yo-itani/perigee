from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle, RecordId
from contexts.record.infrastructure.tables import ActionItemTable
from shared.domain.value_objects import UserId


class SqlAlchemyActionItemRepository(ActionItemRepository):
    """SQLAlchemy-based implementation of ActionItemRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: ActionItemId) -> ActionItem | None:
        stmt = select(ActionItemTable).where(ActionItemTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: ActionItem) -> None:
        existing = await self._session.get(ActionItemTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _insert(self, entity: ActionItem) -> None:
        action_item_row = ActionItemTable(
            id=str(entity.id.value),
            counterpart_id=str(entity.counterpart_id.value),
            record_id=str(entity.record_id.value),
            title=entity.title.value,
            is_completed=entity.is_completed,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(action_item_row)
        await self._session.flush()

    async def _update(self, entity: ActionItem, existing: ActionItemTable) -> None:
        existing.is_completed = entity.is_completed
        existing.updated_at = entity.updated_at
        await self._session.flush()

    @staticmethod
    def _to_entity(row: ActionItemTable) -> ActionItem:
        return ActionItem(
            id=ActionItemId.from_str(row.id),
            counterpart_id=UserId.from_str(row.counterpart_id),
            record_id=RecordId.from_str(row.record_id),
            title=ActionItemTitle(row.title),
            _is_completed=row.is_completed,
            created_at=row.created_at,
            _updated_at=row.updated_at,
        )
