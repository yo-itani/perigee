"""Use case: Delete an ActionItem from a Record.

The organizer deletes an action item during a 1-on-1 session.
After a successful commit the ActionItemDeleted domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.events import ActionItemDeleted
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId, RecordStatus
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


class ActionItemNotFoundError(Exception):
    """Raised when the specified action item does not exist."""

    def __init__(self, action_item_id: ActionItemId) -> None:
        self.action_item_id = action_item_id
        super().__init__(f"Action item not found: {action_item_id.value}")


@dataclass(frozen=True)
class DeleteActionItemInput:
    """Input DTO for DeleteActionItemUseCase."""

    record_id: RecordId
    action_item_id: ActionItemId
    actor_id: UserId


@dataclass(frozen=True)
class DeleteActionItemOutput:
    """Output DTO for DeleteActionItemUseCase."""

    action_item_id: ActionItemId


class DeleteActionItemUseCase:
    """Delete an action item from a record.

    Workflow:
    1. Load the record and verify it exists.
    2. Verify the actor is the organizer.
    3. Verify the record is still in DRAFT status.
    4. Load the action item and verify it belongs to the record.
    5. Delete the action item within a transaction.
    6. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        action_item_repository: ActionItemRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._action_item_repository = action_item_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(self, input_dto: DeleteActionItemInput) -> DeleteActionItemOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            # Only organizer may delete action items
            if input_dto.actor_id != record.organizer_id:
                raise UnauthorizedOperationError(
                    "Only the organizer can delete action items."
                )

            # Record must still be in draft
            if record.status != RecordStatus.DRAFT:
                raise RecordAlreadyPublishedError("Record is already published.")

            action_item = await self._action_item_repository.get_by_id(
                input_dto.action_item_id
            )
            if action_item is None:
                raise ActionItemNotFoundError(input_dto.action_item_id)

            # Verify action item belongs to this record
            if action_item.record_id != input_dto.record_id:
                raise ActionItemNotFoundError(input_dto.action_item_id)

            await self._action_item_repository.delete(input_dto.action_item_id)

        # Dispatch events after successful commit
        events: list[DomainEvent] = [
            ActionItemDeleted(
                occurred_at=now,
                action_item_id=input_dto.action_item_id,
                record_id=input_dto.record_id,
                deleted_by=input_dto.actor_id,
            )
        ]
        await self._event_dispatcher.dispatch(events)

        return DeleteActionItemOutput(action_item_id=input_dto.action_item_id)
