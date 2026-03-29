from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId, RecordStatus
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from shared.domain.value_objects import UserId
from tests.helpers import create_test_user

pytestmark = pytest.mark.integration


def _make_record(
    *,
    organizer_id: UserId,
    counterpart_id: UserId,
    schedule_id: ScheduleId | None = None,
    now: datetime | None = None,
) -> Record:
    return Record.create(
        organizer_id=organizer_id,
        counterpart_id=counterpart_id,
        conducted_at=datetime(2026, 3, 20, 14, 0),
        schedule_id=schedule_id,
        now=now or datetime(2026, 3, 20, 10, 0),
    )


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_record(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)

        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)

        assert loaded is not None
        assert loaded.id == record.id
        assert loaded.organizer_id == organizer
        assert loaded.counterpart_id == counterpart
        assert loaded.memo == Memo("")
        assert loaded.status == RecordStatus.DRAFT
        assert loaded.viewers == []
        assert loaded.conducted_at == record.conducted_at
        assert loaded.schedule_id is None

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRecordRepository(session)
        result = await repo.get_by_id(RecordId.generate())
        assert result is None


class TestRecordUpdate:
    """save() with updates to memo, status, and viewers."""

    async def test_update_memo_and_status(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)

        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        await repo.save(record)
        await session.commit()

        # Update memo
        record.update_memo(
            memo=Memo("Updated memo content"),
            actor_id=organizer,
            now=datetime(2026, 3, 20, 12, 0),
        )
        # Publish
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 13, 0))
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        assert loaded.memo == Memo("Updated memo content")
        assert loaded.status == RecordStatus.PUBLISHED

    async def test_save_with_viewers(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        viewer1 = await create_test_user(session)
        viewer2 = await create_test_user(session)

        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.set_viewers(
            viewer_ids=[viewer1, viewer2],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        loaded_viewer_ids = set(loaded.viewers)
        assert loaded_viewer_ids == {viewer1, viewer2}

    async def test_update_viewers_replace(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        viewer1 = await create_test_user(session)
        viewer2 = await create_test_user(session)
        viewer3 = await create_test_user(session)

        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.set_viewers(
            viewer_ids=[viewer1, viewer2],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )
        await repo.save(record)
        await session.commit()
        # Clear identity map so the next session.get() fetches fresh from DB
        # with selectin-loaded relationships (avoids MissingGreenlet).
        session.expunge_all()

        # Replace viewers: remove viewer1, keep viewer2, add viewer3
        record.set_viewers(
            viewer_ids=[viewer2, viewer3],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 12, 0),
        )
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        loaded_viewer_ids = set(loaded.viewers)
        assert loaded_viewer_ids == {viewer2, viewer3}

    async def test_update_viewers_to_empty(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        viewer1 = await create_test_user(session)

        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.set_viewers(
            viewer_ids=[viewer1],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )
        await repo.save(record)
        await session.commit()
        # Clear identity map so the next session.get() fetches fresh from DB
        # with selectin-loaded relationships (avoids MissingGreenlet).
        session.expunge_all()

        # Clear all viewers
        record.set_viewers(
            viewer_ids=[],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 12, 0),
        )
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        assert loaded.viewers == []

    async def test_save_with_schedule_id(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        schedule_id = ScheduleId.generate()

        record = _make_record(
            organizer_id=organizer,
            counterpart_id=counterpart,
            schedule_id=schedule_id,
        )
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        assert loaded.schedule_id == schedule_id

    async def test_save_without_schedule_id(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRecordRepository(session)
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)

        record = _make_record(
            organizer_id=organizer,
            counterpart_id=counterpart,
            schedule_id=None,
        )
        await repo.save(record)
        await session.commit()

        loaded = await repo.get_by_id(record.id)
        assert loaded is not None
        assert loaded.schedule_id is None
