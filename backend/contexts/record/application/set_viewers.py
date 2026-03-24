"""Use case: Set viewers for a Record.

The organizer can add or change the viewers list. This is allowed
both before and after publication. After a successful commit the
ViewersChanged domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class SetViewersInput:
    """Input DTO for SetViewersUseCase."""

    record_id: RecordId
    actor_id: UserId
    viewer_ids: list[UserId]


@dataclass(frozen=True)
class SetViewersOutput:
    """Output DTO for SetViewersUseCase."""

    record_id: RecordId


class SetViewersUseCase:
    """Set the viewers list for a record.

    Workflow:
    1. Load the record and verify it exists.
    2. Delegate to the domain method (organizer check + dedup).
    3. Save within a transaction.
    4. Dispatch domain events after commit.

    Note: set_viewers is allowed both before and after publication.
    The domain method handles organizer-only enforcement.
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

    async def execute(self, input_dto: SetViewersInput) -> SetViewersOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            record.set_viewers(
                viewer_ids=input_dto.viewer_ids,
                actor_id=input_dto.actor_id,
                now=now,
            )

            await self._record_repository.save(record)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(record.collect_events())
        await self._event_dispatcher.dispatch(events)

        return SetViewersOutput(record_id=record.id)
