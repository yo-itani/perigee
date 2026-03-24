"""Use case: Create a Record from a confirmed Schedule.

The organizer specifies a confirmed schedule and a conducted_at datetime.
A new Record is created in DRAFT status, linked to the schedule via
schedule_id.  If the schedule is still in Requested status, it is
auto-confirmed as a side-effect.

After a successful commit the RecordCreated domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleId, ScheduleStatus
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class ScheduleNotFoundError(Exception):
    """Raised when the specified schedule does not exist."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id.value}")


class ScheduleCancelledError(Exception):
    """Raised when trying to create a record from a cancelled schedule."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule is cancelled: {schedule_id.value}")


@dataclass(frozen=True)
class CreateRecordFromScheduleInput:
    """Input DTO for CreateRecordFromScheduleUseCase."""

    schedule_id: ScheduleId
    actor_id: UserId
    conducted_at: datetime


@dataclass(frozen=True)
class CreateRecordFromScheduleOutput:
    """Output DTO for CreateRecordFromScheduleUseCase."""

    record_id: RecordId


class CreateRecordFromScheduleUseCase:
    """Create a Record from a confirmed Schedule.

    Workflow:
    1. Load the schedule and validate it is not cancelled.
    2. Verify the actor is the organizer of the schedule.
    3. If the schedule is in Requested status, auto-confirm it.
    4. Create a new Record in DRAFT status linked to the schedule.
    5. Save all changes within a single transaction.
    6. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        schedule_repository: ScheduleRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._schedule_repository = schedule_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(
        self, input_dto: CreateRecordFromScheduleInput
    ) -> CreateRecordFromScheduleOutput:
        async with self._unit_of_work:
            schedule = await self._schedule_repository.get_by_id(input_dto.schedule_id)
            if schedule is None:
                raise ScheduleNotFoundError(input_dto.schedule_id)

            if schedule.status == ScheduleStatus.CANCELLED:
                raise ScheduleCancelledError(input_dto.schedule_id)

            if input_dto.actor_id != schedule.organizer_id:
                raise UnauthorizedOperationError(
                    "Only the organizer can create a record."
                )

            # Auto-confirm if still requested
            if schedule.status == ScheduleStatus.REQUESTED:
                schedule.auto_confirm(now=input_dto.conducted_at)
                await self._schedule_repository.save(schedule)

            record = Record.create(
                organizer_id=schedule.organizer_id,
                counterpart_id=schedule.counterpart_id,
                conducted_at=input_dto.conducted_at,
                schedule_id=input_dto.schedule_id,
                now=input_dto.conducted_at,
            )

            await self._record_repository.save(record)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        all_events: list[DomainEvent] = list(record.collect_events())
        all_events = list(schedule.collect_events()) + all_events
        await self._event_dispatcher.dispatch(all_events)

        return CreateRecordFromScheduleOutput(record_id=record.id)
