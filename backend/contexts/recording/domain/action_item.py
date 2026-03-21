from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from contexts.recording.domain.events import ActionItemAdded, ActionItemCompleted
from contexts.recording.domain.value_objects import ActionItemId, RecordId
from shared.domain.value_objects import UserId


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
    title: str
    is_completed: bool
    created_at: datetime
    events: list[ActionItemAdded | ActionItemCompleted] = field(
        default_factory=list, repr=False
    )

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
            raise PermissionError("Only the organizer can add action items.")
        if not title.strip():
            raise ValueError("Action item title must not be empty.")
        action_item_id = ActionItemId.generate()
        ts = now or datetime.now()
        action_item = ActionItem(
            id=action_item_id,
            counterpart_id=counterpart_id,
            record_id=record_id,
            title=title,
            is_completed=False,
            created_at=ts,
        )
        action_item.events.append(
            ActionItemAdded(
                action_item_id=action_item_id,
                counterpart_id=counterpart_id,
                record_id=record_id,
                title=title,
                created_at=ts,
            )
        )
        return action_item

    def complete(self, *, actor_id: UserId, now: datetime) -> None:
        """Mark as completed. Only the counterpart may complete."""
        if actor_id != self.counterpart_id:
            raise PermissionError("Only the counterpart can complete action items.")
        if self.is_completed:
            raise ValueError("Action item is already completed.")
        self.is_completed = True
        self.events.append(
            ActionItemCompleted(
                action_item_id=self.id,
                counterpart_id=self.counterpart_id,
                completed_at=now,
            )
        )
