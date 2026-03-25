"""SQLAlchemy implementation of ReminderLogRepository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.notification.domain.reminder_log import ReminderLog
from contexts.notification.domain.reminder_log_repository import ReminderLogRepository
from contexts.notification.domain.value_objects import ReminderLogId
from contexts.notification.infrastructure.tables import ReminderLogTable
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId


class SqlAlchemyReminderLogRepository(ReminderLogRepository):
    """SQLAlchemy-based implementation of ReminderLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(
        self,
        schedule_id: ScheduleId,
        user_id: UserId,
        scheduled_at: datetime,
    ) -> bool:
        stmt = select(ReminderLogTable.id).where(
            ReminderLogTable.schedule_id == str(schedule_id.value),
            ReminderLogTable.user_id == str(user_id.value),
            ReminderLogTable.scheduled_at == scheduled_at,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save(self, log: ReminderLog) -> None:
        row = ReminderLogTable(
            id=str(log.id.value),
            schedule_id=str(log.schedule_id.value),
            user_id=str(log.user_id.value),
            scheduled_at=log.scheduled_at,
            sent_at=log.sent_at,
            reminder_minutes_before=log.reminder_minutes_before,
        )
        self._session.add(row)
        await self._session.flush()

    @staticmethod
    def _to_entity(row: ReminderLogTable) -> ReminderLog:
        return ReminderLog(
            id=ReminderLogId.from_str(row.id),
            schedule_id=ScheduleId.from_str(row.schedule_id),
            user_id=UserId.from_str(row.user_id),
            scheduled_at=row.scheduled_at,
            _sent_at=row.sent_at,
            _reminder_minutes_before=row.reminder_minutes_before,
        )
