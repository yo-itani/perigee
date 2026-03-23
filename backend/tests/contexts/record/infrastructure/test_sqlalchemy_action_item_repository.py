from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle
from contexts.record.infrastructure.sqlalchemy_action_item_repository import (
    SqlAlchemyActionItemRepository,
)
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable

pytestmark = pytest.mark.integration


async def _create_user(session: AsyncSession) -> UserId:
    """Insert a user row and return its UserId (needed for FK constraints)."""
    user_id = UserId.generate()
    session.add(UserTable(id=str(user_id.value)))
    await session.flush()
    return user_id


async def _create_record(
    session: AsyncSession, organizer: UserId, counterpart: UserId
) -> Record:
    """Create and persist a Record (needed for FK constraints on action items)."""
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=datetime(2026, 3, 20, 14, 0),
        now=datetime(2026, 3, 20, 10, 0),
    )
    repo = SqlAlchemyRecordRepository(session)
    await repo.save(record)
    await session.flush()
    return record


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_action_item(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyActionItemRepository(session)
        action_item = ActionItem.create(
            counterpart_id=counterpart,
            record_id=record.id,
            title=ActionItemTitle("Review PR #42"),
            actor_id=organizer,
            organizer_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(action_item)
        await session.commit()

        loaded = await repo.get_by_id(action_item.id)

        assert loaded is not None
        assert loaded.id == action_item.id
        assert loaded.counterpart_id == counterpart
        assert loaded.record_id == record.id
        assert loaded.title == ActionItemTitle("Review PR #42")
        assert loaded.is_completed is False

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyActionItemRepository(session)
        result = await repo.get_by_id(ActionItemId.generate())
        assert result is None


class TestActionItemUpdate:
    """save() with updates (complete)."""

    async def test_complete_action_item(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyActionItemRepository(session)
        action_item = ActionItem.create(
            counterpart_id=counterpart,
            record_id=record.id,
            title=ActionItemTitle("Write tests"),
            actor_id=organizer,
            organizer_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(action_item)
        await session.commit()

        # Complete the action item
        action_item.complete(
            actor_id=counterpart,
            now=datetime(2026, 3, 20, 16, 0),
        )
        await repo.save(action_item)
        await session.commit()

        loaded = await repo.get_by_id(action_item.id)
        assert loaded is not None
        assert loaded.is_completed is True
