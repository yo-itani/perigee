"""Use case: Add a Retrospective to a published Record.

Only the organizer or counterpart can add a retrospective. Viewers
cannot. Retrospectives are insert-only. After a successful commit
the RetrospectiveAdded domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.exceptions import (
    RecordNotPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.retrospective import Retrospective
from contexts.record.domain.retrospective_body import RetrospectiveBody
from contexts.record.domain.retrospective_repository import RetrospectiveRepository
from contexts.record.domain.value_objects import RecordId, RecordStatus, RetrospectiveId
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
class AddRetrospectiveInput:
    """Input DTO for AddRetrospectiveUseCase."""

    record_id: RecordId
    actor_id: UserId
    body: RetrospectiveBody


@dataclass(frozen=True)
class AddRetrospectiveOutput:
    """Output DTO for AddRetrospectiveUseCase."""

    retrospective_id: RetrospectiveId


class AddRetrospectiveUseCase:
    """Add a retrospective to a published record.

    Workflow:
    1. Load the record and verify it exists.
    2. Verify the record is published.
    3. Verify the actor is organizer or counterpart (viewers cannot).
    4. Create the retrospective (insert-only).
    5. Save within a transaction.
    6. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        retrospective_repository: RetrospectiveRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._retrospective_repository = retrospective_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(self, input_dto: AddRetrospectiveInput) -> AddRetrospectiveOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            if record.status != RecordStatus.PUBLISHED:
                raise RecordNotPublishedError(
                    "Retrospectives can only be added to published records."
                )

            if (
                input_dto.actor_id != record.organizer_id
                and input_dto.actor_id != record.counterpart_id
            ):
                raise UnauthorizedOperationError(
                    "Only the organizer or counterpart can add retrospectives."
                )

            retrospective = Retrospective.create(
                record_id=record.id,
                author_id=input_dto.actor_id,
                body=input_dto.body,
                now=now,
            )

            await self._retrospective_repository.save(retrospective)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(retrospective.collect_events())
        await self._event_dispatcher.dispatch(events)

        return AddRetrospectiveOutput(retrospective_id=retrospective.id)
