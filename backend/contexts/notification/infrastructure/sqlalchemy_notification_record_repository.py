"""SQLAlchemy implementation of NotificationRecordRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.notification_record_repository import (
    NotificationRecordRepository,
)
from contexts.notification.domain.value_objects import (
    NotificationRecordId,
    NotificationType,
)
from contexts.notification.infrastructure.tables import NotificationRecordTable
from foundation.datetime_utils import to_aware_utc, to_aware_utc_optional, to_naive_utc
from shared.domain.value_objects import UserId


class SqlAlchemyNotificationRecordRepository(NotificationRecordRepository):
    """SQLAlchemy-based implementation of NotificationRecordRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, record_id: NotificationRecordId
    ) -> NotificationRecord | None:
        row = await self._session.get(NotificationRecordTable, str(record_id.value))
        if row is None:
            return None
        return self._to_entity(row)

    async def list_by_recipient(
        self,
        recipient_id: UserId,
        *,
        unread_only: bool = False,
    ) -> list[NotificationRecord]:
        stmt = (
            select(NotificationRecordTable)
            .where(NotificationRecordTable.recipient_id == str(recipient_id.value))
            .order_by(NotificationRecordTable.created_at.desc())
        )
        if unread_only:
            stmt = stmt.where(NotificationRecordTable.is_read.is_(False))

        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def save(self, record: NotificationRecord) -> None:
        existing = await self._session.get(
            NotificationRecordTable, str(record.id.value)
        )
        if existing is None:
            row = NotificationRecordTable(
                id=str(record.id.value),
                recipient_id=str(record.recipient_id.value),
                notification_type=record.notification_type.value,
                title=record.title,
                body=record.body,
                link=record.link,
                is_read=record.is_read,
                read_at=(to_naive_utc(record.read_at) if record.read_at else None),
                created_at=to_naive_utc(record.created_at),
            )
            self._session.add(row)
        else:
            existing.is_read = record.is_read
            existing.read_at = to_naive_utc(record.read_at) if record.read_at else None

        await self._session.flush()

    @staticmethod
    def _to_entity(row: NotificationRecordTable) -> NotificationRecord:
        return NotificationRecord(
            id=NotificationRecordId.from_str(row.id),
            recipient_id=UserId.from_str(row.recipient_id),
            notification_type=NotificationType(row.notification_type),
            title=row.title,
            body=row.body,
            link=row.link,
            _is_read=row.is_read,
            _read_at=to_aware_utc_optional(row.read_at),
            created_at=to_aware_utc(row.created_at),
        )
