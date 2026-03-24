from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.confirmation_request import ConfirmationRequest
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import (
    ConfirmationRequestId,
    ConfirmationRequestType,
    ConfirmationResolution,
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
)
from contexts.preparation.infrastructure.tables import (
    ConfirmationRequestTable,
    ScheduleTable,
)
from shared.domain.value_objects import UserId


class SqlAlchemyScheduleRepository(ScheduleRepository):
    """SQLAlchemy-based implementation of ScheduleRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: ScheduleId) -> Schedule | None:
        stmt = select(ScheduleTable).where(ScheduleTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def get_by_schedule_group_id(
        self, schedule_group_id: ScheduleGroupId
    ) -> list[Schedule]:
        stmt = select(ScheduleTable).where(
            ScheduleTable.schedule_group_id == str(schedule_group_id.value)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def save(self, entity: Schedule) -> None:
        existing = await self._session.get(ScheduleTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _insert(self, entity: Schedule) -> None:
        schedule_row = ScheduleTable(
            id=str(entity.id.value),
            organizer_id=str(entity.organizer_id.value),
            counterpart_id=str(entity.counterpart_id.value),
            schedule_group_id=(
                str(entity.schedule_group_id.value)
                if entity.schedule_group_id
                else None
            ),
            title=entity.title.value,
            scheduled_at=entity.scheduled_at,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        for cr in entity.confirmation_requests:
            cr_row = ConfirmationRequestTable(
                id=str(cr.id.value),
                schedule_id=str(entity.id.value),
                request_type=cr.request_type.value,
                requested_by=str(cr.requested_by.value),
                proposed_at=cr.proposed_at,
                resolution=cr.resolution.value,
                resolved_by=str(cr.resolved_by.value) if cr.resolved_by else None,
                created_at=cr.created_at,
                updated_at=entity.created_at,
            )
            schedule_row.confirmation_requests.append(cr_row)
        self._session.add(schedule_row)
        await self._session.flush()

    async def _update(self, entity: Schedule, existing: ScheduleTable) -> None:
        now = datetime.now(UTC)

        existing.organizer_id = str(entity.organizer_id.value)
        existing.counterpart_id = str(entity.counterpart_id.value)
        existing.schedule_group_id = (
            str(entity.schedule_group_id.value) if entity.schedule_group_id else None
        )
        existing.title = entity.title.value
        existing.scheduled_at = entity.scheduled_at
        existing.status = entity.status.value
        existing.updated_at = now

        # Reconcile confirmation requests
        existing_cr_map: dict[str, ConfirmationRequestTable] = {
            cr.id: cr for cr in existing.confirmation_requests
        }
        entity_cr_ids: set[str] = set()

        for cr in entity.confirmation_requests:
            cr_id = str(cr.id.value)
            entity_cr_ids.add(cr_id)
            if cr_id in existing_cr_map:
                db_cr = existing_cr_map[cr_id]
                db_cr.request_type = cr.request_type.value
                db_cr.requested_by = str(cr.requested_by.value)
                db_cr.proposed_at = cr.proposed_at
                db_cr.resolution = cr.resolution.value
                db_cr.resolved_by = (
                    str(cr.resolved_by.value) if cr.resolved_by else None
                )
                db_cr.updated_at = now
            else:
                new_cr = ConfirmationRequestTable(
                    id=cr_id,
                    schedule_id=str(entity.id.value),
                    request_type=cr.request_type.value,
                    requested_by=str(cr.requested_by.value),
                    proposed_at=cr.proposed_at,
                    resolution=cr.resolution.value,
                    resolved_by=(str(cr.resolved_by.value) if cr.resolved_by else None),
                    created_at=cr.created_at,
                    updated_at=cr.created_at,
                )
                existing.confirmation_requests.append(new_cr)

        for cr_id, db_cr in existing_cr_map.items():
            if cr_id not in entity_cr_ids:
                existing.confirmation_requests.remove(db_cr)

        await self._session.flush()

    @staticmethod
    def _to_entity(row: ScheduleTable) -> Schedule:
        confirmation_requests = [
            ConfirmationRequest(
                id=ConfirmationRequestId.from_str(cr.id),
                request_type=ConfirmationRequestType(cr.request_type),
                requested_by=UserId.from_str(cr.requested_by),
                proposed_at=cr.proposed_at,
                _resolution=ConfirmationResolution(cr.resolution),
                _resolved_by=(
                    UserId.from_str(cr.resolved_by) if cr.resolved_by else None
                ),
                created_at=cr.created_at,
            )
            for cr in row.confirmation_requests
        ]
        return Schedule(
            id=ScheduleId.from_str(row.id),
            organizer_id=UserId.from_str(row.organizer_id),
            counterpart_id=UserId.from_str(row.counterpart_id),
            schedule_group_id=(
                ScheduleGroupId.from_str(row.schedule_group_id)
                if row.schedule_group_id
                else None
            ),
            _title=ScheduleTitle(row.title),
            _scheduled_at=row.scheduled_at,
            _status=ScheduleStatus(row.status),
            _confirmation_requests=confirmation_requests,
            created_at=row.created_at,
            _updated_at=row.updated_at,
        )
