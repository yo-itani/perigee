"""Use case: Complete an ActionItem.

The counterpart marks an action item as completed.
Action items are tied to the counterpart (person), not to a record.
After a successful commit the ActionItemCompleted domain event is dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.value_objects import ActionItemId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class ActionItemNotFoundError(Exception):
    """Raised when the specified action item does not exist."""

    def __init__(self, action_item_id: ActionItemId) -> None:
        self.action_item_id = action_item_id
        super().__init__(f"Action item not found: {action_item_id.value}")


@dataclass(frozen=True)
class CompleteActionItemInput:
    """Input DTO for CompleteActionItemUseCase."""

    action_item_id: ActionItemId
    actor_id: UserId


@dataclass(frozen=True)
class CompleteActionItemOutput:
    """Output DTO for CompleteActionItemUseCase."""

    action_item_id: ActionItemId


class CompleteActionItemUseCase:
    """Complete an action item.

    Workflow:
    1. Load the action item and verify it exists.
    2. Complete (counterpart check delegated to ActionItem.complete).
    3. Save within a transaction.
    4. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        action_item_repository: ActionItemRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._action_item_repository = action_item_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(
        self, input_dto: CompleteActionItemInput
    ) -> CompleteActionItemOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            action_item = await self._action_item_repository.get_by_id(
                input_dto.action_item_id
            )
            if action_item is None:
                raise ActionItemNotFoundError(input_dto.action_item_id)

            action_item.complete(actor_id=input_dto.actor_id, now=now)

            await self._action_item_repository.save(action_item)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(action_item.collect_events())
        await self._event_dispatcher.dispatch(events)

        return CompleteActionItemOutput(action_item_id=action_item.id)
