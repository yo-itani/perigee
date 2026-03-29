from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.comment import Comment
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.exceptions import CommentAlreadyExistsError
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import CommentId
from contexts.record.infrastructure.sqlalchemy_comment_repository import (
    SqlAlchemyCommentRepository,
)
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from shared.domain.value_objects import UserId
from tests.helpers import create_test_user

pytestmark = pytest.mark.integration


async def _create_record(
    session: AsyncSession, organizer: UserId, counterpart: UserId
) -> Record:
    """Create and persist a Record (needed for FK constraints on comments)."""
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=datetime(2026, 3, 20, 14, 0, tzinfo=UTC),
        now=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
    )
    repo = SqlAlchemyRecordRepository(session)
    await repo.save(record)
    await session.flush()
    return record


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_comment(self, session: AsyncSession) -> None:
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyCommentRepository(session)
        comment = Comment.create(
            record_id=record.id,
            author_id=organizer,
            body=CommentBody("Great session!"),
            now=datetime(2026, 3, 20, 15, 0, tzinfo=UTC),
        )
        await repo.save(comment)
        await session.commit()

        loaded = await repo.get_by_id(comment.id)

        assert loaded is not None
        assert loaded.id == comment.id
        assert loaded.record_id == record.id
        assert loaded.author_id == organizer
        assert loaded.body == CommentBody("Great session!")

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommentRepository(session)
        result = await repo.get_by_id(CommentId.generate())
        assert result is None


class TestInsertOnly:
    """Comment is insert-only: save() raises on duplicate."""

    async def test_save_existing_comment_raises(self, session: AsyncSession) -> None:
        organizer = await create_test_user(session)
        counterpart = await create_test_user(session)
        record = await _create_record(session, organizer, counterpart)

        repo = SqlAlchemyCommentRepository(session)
        comment = Comment.create(
            record_id=record.id,
            author_id=organizer,
            body=CommentBody("First comment"),
            now=datetime(2026, 3, 20, 15, 0, tzinfo=UTC),
        )
        await repo.save(comment)
        await session.commit()

        with pytest.raises(CommentAlreadyExistsError):
            await repo.save(comment)
