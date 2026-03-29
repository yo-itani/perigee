"""Integration tests for SqlAlchemyReminderLogRepository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.notification.domain.reminder_log import ReminderLog
from contexts.notification.domain.value_objects import ReminderLogId
from contexts.notification.infrastructure.sqlalchemy_reminder_log_repository import (
    SqlAlchemyReminderLogRepository,
)
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId

pytestmark = pytest.mark.integration

SCHEDULED_AT = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
SENT_AT = datetime(2026, 3, 31, 9, 30, tzinfo=UTC)


def _make_log(
    *,
    schedule_id: ScheduleId | None = None,
    user_id: UserId | None = None,
    scheduled_at: datetime = SCHEDULED_AT,
) -> ReminderLog:
    return ReminderLog(
        id=ReminderLogId.generate(),
        schedule_id=schedule_id or ScheduleId.generate(),
        user_id=user_id or UserId.generate(),
        scheduled_at=scheduled_at,
        _sent_at=SENT_AT,
        _reminder_minutes_before=30,
    )


class TestUniqueConstraint:
    """Verify the DB unique constraint on (schedule_id, user_id, scheduled_at)."""

    async def test_duplicate_save_raises_integrity_error(
        self, session: AsyncSession
    ) -> None:
        """Same composite key violates the unique constraint."""
        repo = SqlAlchemyReminderLogRepository(session)

        schedule_id = ScheduleId.generate()
        user_id = UserId.generate()

        log1 = _make_log(schedule_id=schedule_id, user_id=user_id)
        await repo.save(log1)
        await session.flush()

        log2 = _make_log(schedule_id=schedule_id, user_id=user_id)
        with pytest.raises(IntegrityError):
            await repo.save(log2)
            await session.flush()

    async def test_different_scheduled_at_allows_save(
        self, session: AsyncSession
    ) -> None:
        """Different scheduled_at with same schedule_id/user_id is allowed."""
        repo = SqlAlchemyReminderLogRepository(session)

        schedule_id = ScheduleId.generate()
        user_id = UserId.generate()

        log1 = _make_log(
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
        )
        await repo.save(log1)

        log2 = _make_log(
            schedule_id=schedule_id,
            user_id=user_id,
            scheduled_at=datetime(2026, 4, 5, 14, 0, tzinfo=UTC),
        )
        await repo.save(log2)
        await session.flush()

        assert await repo.exists(
            schedule_id, user_id, datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
        )
        assert await repo.exists(
            schedule_id, user_id, datetime(2026, 4, 5, 14, 0, tzinfo=UTC)
        )


class TestExistsQuery:
    """Verify the exists() query works correctly."""

    async def test_exists_returns_false_when_empty(self, session: AsyncSession) -> None:
        """exists() returns False when no matching log exists."""
        repo = SqlAlchemyReminderLogRepository(session)
        result = await repo.exists(
            ScheduleId.generate(), UserId.generate(), SCHEDULED_AT
        )
        assert result is False

    async def test_exists_returns_true_after_save(self, session: AsyncSession) -> None:
        """exists() returns True after saving a matching log."""
        repo = SqlAlchemyReminderLogRepository(session)

        log = _make_log()
        await repo.save(log)
        await session.flush()

        result = await repo.exists(log.schedule_id, log.user_id, log.scheduled_at)
        assert result is True
