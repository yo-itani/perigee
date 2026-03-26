from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ReadStatusId, RecordId
from contexts.record.infrastructure.sqlalchemy_read_status_repository import (
    SqlAlchemyReadStatusRepository,
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
    """Create and persist a Record (needed for FK constraints)."""
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

    async def test_save_and_restore_read_status(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyReadStatusRepository(session)
        rs = ReadStatus.create(
            record_id=record.id,
            user_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(rs)
        await session.commit()

        loaded = await repo.get_by_id(rs.id)

        assert loaded is not None
        assert loaded.id == rs.id
        assert loaded.record_id == record.id
        assert loaded.user_id == organizer
        assert loaded.last_viewed_at == datetime(2026, 3, 20, 15, 0)

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyReadStatusRepository(session)
        result = await repo.get_by_id(ReadStatusId.generate())
        assert result is None


class TestSaveUpdate:
    """save() updates an existing ReadStatus."""

    async def test_save_updates_last_viewed_at(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyReadStatusRepository(session)
        rs = ReadStatus.create(
            record_id=record.id,
            user_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(rs)
        await session.commit()

        rs.mark_viewed(now=datetime(2026, 3, 20, 18, 0))
        await repo.save(rs)
        await session.commit()

        loaded = await repo.get_by_id(rs.id)
        assert loaded is not None
        assert loaded.last_viewed_at == datetime(2026, 3, 20, 18, 0)


class TestFindByRecordAndUser:
    """find_by_record_and_user() queries."""

    async def test_find_existing(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyReadStatusRepository(session)
        rs = ReadStatus.create(
            record_id=record.id,
            user_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(rs)
        await session.commit()

        found = await repo.find_by_record_and_user(record.id, organizer)
        assert found is not None
        assert found.id == rs.id

    async def test_find_returns_none_when_no_match(self, session: AsyncSession) -> None:
        repo = SqlAlchemyReadStatusRepository(session)
        result = await repo.find_by_record_and_user(
            RecordId.generate(), UserId.generate()
        )
        assert result is None


class TestDeleteByRecordAndUser:
    """delete_by_record_and_user() removes the matching row."""

    async def test_delete_existing(self, session: AsyncSession) -> None:
        organizer = await _create_user(session)
        counterpart = await _create_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyReadStatusRepository(session)
        rs = ReadStatus.create(
            record_id=record.id,
            user_id=organizer,
            now=datetime(2026, 3, 20, 15, 0),
        )
        await repo.save(rs)
        await session.commit()

        await repo.delete_by_record_and_user(record.id, organizer)
        await session.commit()

        found = await repo.find_by_record_and_user(record.id, organizer)
        assert found is None

    async def test_delete_nonexistent_is_noop(self, session: AsyncSession) -> None:
        """delete_by_record_and_user is a no-op when no matching row exists."""
        repo = SqlAlchemyReadStatusRepository(session)
        # Should not raise
        await repo.delete_by_record_and_user(RecordId.generate(), UserId.generate())
