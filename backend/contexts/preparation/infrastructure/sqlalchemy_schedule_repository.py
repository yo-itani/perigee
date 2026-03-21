"""SQLAlchemy implementation of ScheduleRepository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.confirmation_request import ConfirmationRequest
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import (
    ConfirmationRequestId,
    ConfirmationRequestType,
    ConfirmationResolution,
    ScheduleId,
    ScheduleStatus,
)
from contexts.preparation.infrastructure.models import (
    ConfirmationRequestRow,
    ScheduleRow,
)
from shared.domain.value_objects import UserId


class SqlAlchemyScheduleRepository(ScheduleRepository):
    """SQLAlchemy-based repository for Schedule aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, schedule_id: ScheduleId) -> Schedule | None:
        """Retrieve a Schedule by its ID, or None if not found."""
        stmt = select(ScheduleRow).where(ScheduleRow.id == str(schedule_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _row_to_entity(row)

    async def save(self, schedule: Schedule) -> None:
        """Persist a Schedule (insert or update via merge)."""
        row = _entity_to_row(schedule)
        await self._session.merge(row)
        await self._session.flush()


def _row_to_entity(row: ScheduleRow) -> Schedule:
    """Map a ScheduleRow (with loaded ConfirmationRequestRows) to a domain Schedule."""
    confirmation_requests = [
        ConfirmationRequest(
            id=ConfirmationRequestId.from_str(cr.id),
            request_type=ConfirmationRequestType(cr.request_type),
            requested_by=UserId.from_str(cr.requested_by),
            proposed_at=cr.proposed_at,
            _resolution=ConfirmationResolution(cr.resolution),
            _resolved_by=UserId.from_str(cr.resolved_by) if cr.resolved_by else None,
            created_at=cr.created_at,
        )
        for cr in row.confirmation_requests
    ]

    return Schedule(
        id=ScheduleId.from_str(row.id),
        organizer_id=UserId.from_str(row.organizer_id),
        counterpart_id=UserId.from_str(row.counterpart_id),
        _scheduled_at=row.scheduled_at,
        _status=ScheduleStatus(row.status),
        _confirmation_requests=confirmation_requests,
        created_at=row.created_at,
        _updated_at=row.updated_at,
    )


def _entity_to_row(schedule: Schedule) -> ScheduleRow:
    """Map a domain Schedule to a ScheduleRow (with child rows)."""
    row = ScheduleRow(
        id=str(schedule.id.value),
        organizer_id=str(schedule.organizer_id.value),
        counterpart_id=str(schedule.counterpart_id.value),
        scheduled_at=schedule.scheduled_at,
        status=schedule.status.value,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )
    row.confirmation_requests = [
        ConfirmationRequestRow(
            id=str(cr.id.value),
            schedule_id=str(schedule.id.value),
            request_type=cr.request_type.value,
            requested_by=str(cr.requested_by.value),
            proposed_at=cr.proposed_at,
            resolution=cr.resolution.value,
            resolved_by=str(cr.resolved_by.value) if cr.resolved_by else None,
            created_at=cr.created_at,
        )
        for cr in schedule.confirmation_requests
    ]
    return row
