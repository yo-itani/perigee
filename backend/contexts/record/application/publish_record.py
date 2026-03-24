"""Use case: Publish a Record.

The organizer transitions the record from DRAFT to PUBLISHED status.
Viewers are snapshot-confirmed at publish time. After a successful
commit the RecordPublished domain event is dispatched (triggers Slack
notification).
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
class PublishRecordInput:
    """Input DTO for PublishRecordUseCase."""

    record_id: RecordId
    actor_id: UserId
    viewer_ids: list[UserId]


@dataclass(frozen=True)
class PublishRecordOutput:
    """Output DTO for PublishRecordUseCase."""

    record_id: RecordId


class PublishRecordUseCase:
    """Publish a record, confirming viewers as a snapshot.

    Workflow:
    1. Load the record and verify it exists.
    2. Publish (DRAFT -> PUBLISHED one-way transition).
    3. Set viewers (snapshot at publish time).
    4. Save within a transaction.
    5. Dispatch domain events after commit.
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

    async def execute(self, input_dto: PublishRecordInput) -> PublishRecordOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            record.publish(
                actor_id=input_dto.actor_id,
                now=now,
            )
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

        return PublishRecordOutput(record_id=record.id)
