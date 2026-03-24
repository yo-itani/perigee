"""Use case: Create a post-hoc Record (Pattern C).

The organizer creates a record directly without going through
scheduling.  The schedule_id is null.

After a successful commit the RecordCreated domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class CreatePostHocRecordInput:
    """Input DTO for CreatePostHocRecordUseCase."""

    actor_id: UserId
    organizer_id: UserId
    counterpart_id: UserId
    conducted_at: datetime


@dataclass(frozen=True)
class CreatePostHocRecordOutput:
    """Output DTO for CreatePostHocRecordUseCase."""

    record_id: RecordId


class SameUserError(Exception):
    """Raised when organizer and counterpart are the same user."""

    def __init__(self) -> None:
        super().__init__("Organizer and counterpart must be different users.")


class CreatePostHocRecordUseCase:
    """Create a Record without a schedule (post-hoc recording).

    Workflow:
    1. Validate organizer != counterpart.
    2. Create a new Record in DRAFT status with schedule_id = None.
    3. Save within a transaction.
    4. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(
        self, input_dto: CreatePostHocRecordInput
    ) -> CreatePostHocRecordOutput:
        if input_dto.actor_id != input_dto.organizer_id:
            raise UnauthorizedOperationError("Only the organizer can create a record.")

        if input_dto.organizer_id == input_dto.counterpart_id:
            raise SameUserError()

        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = Record.create(
                organizer_id=input_dto.organizer_id,
                counterpart_id=input_dto.counterpart_id,
                conducted_at=input_dto.conducted_at,
                schedule_id=None,
                now=now,
            )

            await self._record_repository.save(record)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(record.collect_events())
        await self._event_dispatcher.dispatch(events)

        return CreatePostHocRecordOutput(record_id=record.id)
