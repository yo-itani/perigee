"""Use case: Create a 1-on-1 record (schedule-based or post-hoc)."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.value_objects import UserId


class CreateRecordService:
    """Application service that creates a new Record in DRAFT status.

    Supports two creation patterns:
    - Schedule-based: organizer starts a 1-on-1 from a confirmed schedule.
    - Post-hoc (Pattern C): organizer creates a record without a schedule.

    The organizer is the only actor allowed to create a record.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        record_repo: RecordRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._record_repo = record_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        *,
        organizer_id: UserId,
        counterpart_id: UserId,
        conducted_at: datetime,
        schedule_id: ScheduleId | None = None,
    ) -> RecordId:
        """Create a record and return its id.

        Args:
            organizer_id: The user creating the record (must be the organizer).
            counterpart_id: The counterpart of the 1-on-1.
            conducted_at: When the 1-on-1 was (or will be) conducted.
            schedule_id: Optional schedule reference for schedule-based creation.

        Returns:
            The id of the newly created record.
        """
        now = datetime.now(UTC)

        record = Record.create(
            organizer_id=organizer_id,
            counterpart_id=counterpart_id,
            conducted_at=conducted_at,
            schedule_id=schedule_id,
            now=now,
        )

        async with self._uow:
            await self._record_repo.save(record)
            events = record.collect_events()
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return record.id
