from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.recording.domain.events import ActionItemAdded, ActionItemCompleted
from contexts.recording.domain.exceptions import (
    ActionItemAlreadyCompletedError,
    UnauthorizedOperationError,
)
from contexts.recording.domain.value_objects import (
    ActionItemId,
    ActionItemTitle,
    RecordId,
)
from shared.domain.value_objects import UserId

type _ActionItemEvent = ActionItemAdded | ActionItemCompleted


@dataclass
class ActionItem:
    """Aggregate root: an action item from a 1-on-1.

    Action items are tied to a counterpart (person), not to a record.
    The record_id tracks which 1-on-1 the item originated from.

    Business rules:
    - Only the organizer may add action items.
    - Only the counterpart may complete action items.
    """

    id: ActionItemId
    counterpart_id: UserId
    record_id: RecordId
    title: ActionItemTitle
    _is_completed: bool
    created_at: datetime
    _events: list[_ActionItemEvent] = field(default_factory=list, repr=False)

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @staticmethod
    def create(
        *,
        counterpart_id: UserId,
        record_id: RecordId,
        title: str,
        actor_id: UserId,
        organizer_id: UserId,
        now: datetime | None = None,
    ) -> ActionItem:
        """Create a new action item. Only the organizer may add."""
        if actor_id != organizer_id:
            raise UnauthorizedOperationError("Only the organizer can add action items.")
        action_item_title = ActionItemTitle(title)
        action_item_id = ActionItemId.generate()
        ts = now or datetime.now(UTC)
        action_item = ActionItem(
            id=action_item_id,
            counterpart_id=counterpart_id,
            record_id=record_id,
            title=action_item_title,
            _is_completed=False,
            created_at=ts,
        )
        action_item._events.append(
            ActionItemAdded(
                action_item_id=action_item_id,
                counterpart_id=counterpart_id,
                record_id=record_id,
                title=action_item_title.value,
                created_at=ts,
            )
        )
        return action_item

    def complete(self, *, actor_id: UserId, now: datetime) -> None:
        """Mark as completed. Only the counterpart may complete."""
        if actor_id != self.counterpart_id:
            raise UnauthorizedOperationError(
                "Only the counterpart can complete action items."
            )
        if self._is_completed:
            raise ActionItemAlreadyCompletedError("Action item is already completed.")
        self._is_completed = True
        self._events.append(
            ActionItemCompleted(
                action_item_id=self.id,
                counterpart_id=self.counterpart_id,
                completed_at=now,
            )
        )

    def collect_events(self) -> list[_ActionItemEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events
