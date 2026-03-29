"""Use case: Add an ActionItem to a Record.

The organizer registers an action item during a 1-on-1 session.
Action items are tied to the counterpart (person), not to the record.
After a successful commit the ActionItemAdded domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle, RecordId
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
class AddActionItemInput:
    """Input DTO for AddActionItemUseCase."""

    record_id: RecordId
    actor_id: UserId
    title: ActionItemTitle


@dataclass(frozen=True)
class AddActionItemOutput:
    """Output DTO for AddActionItemUseCase."""

    action_item_id: ActionItemId


class AddActionItemUseCase:
    """Add an action item to a record.

    Workflow:
    1. Load the record and verify it exists.
    2. Create the action item (organizer check delegated to ActionItem.create).
    3. Save within a transaction.
    4. Dispatch domain events after commit.
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

    async def execute(self, input_dto: AddActionItemInput) -> AddActionItemOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            action_item = ActionItem.create(
                counterpart_id=record.counterpart_id,
                record_id=record.id,
                title=input_dto.title,
                actor_id=input_dto.actor_id,
                organizer_id=record.organizer_id,
                now=now,
            )

            await self._action_item_repository.save(action_item)

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(action_item.collect_events())
        await self._event_dispatcher.dispatch(events)

        return AddActionItemOutput(action_item_id=action_item.id)
