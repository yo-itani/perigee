from datetime import datetime

import pytest

from contexts.recording.domain.action_item import ActionItem
from contexts.recording.domain.events import ActionItemAdded, ActionItemCompleted
from contexts.recording.domain.value_objects import RecordId
from shared.domain.value_objects import UserId


def _make_action_item(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    record_id: RecordId | None = None,
    title: str = "Follow up on project status",
    now: datetime | None = None,
) -> ActionItem:
    """Helper to create an action item with sensible defaults."""
    org = organizer_id or UserId.generate()
    return ActionItem.create(
        counterpart_id=counterpart_id or UserId.generate(),
        record_id=record_id or RecordId.generate(),
        title=title,
        actor_id=org,
        organizer_id=org,
        now=now or datetime(2026, 3, 20, 10, 30),
    )


class TestActionItemCreate:
    def test_creates_with_defaults(self) -> None:
        item = _make_action_item()
        assert item.is_completed is False
        assert item.title == "Follow up on project status"

    def test_only_organizer_can_create(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()

        with pytest.raises(PermissionError, match="Only the organizer"):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="Task",
                actor_id=other,
                organizer_id=organizer,
            )

    def test_title_must_not_be_empty(self) -> None:
        organizer = UserId.generate()

        with pytest.raises(ValueError, match="title must not be empty"):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="   ",
                actor_id=organizer,
                organizer_id=organizer,
            )

    def test_emits_action_item_added_event(self) -> None:
        item = _make_action_item()
        assert len(item.events) == 1
        event = item.events[0]
        assert isinstance(event, ActionItemAdded)
        assert event.action_item_id == item.id
        assert event.title == item.title


class TestActionItemComplete:
    def test_counterpart_can_complete(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        now = datetime(2026, 3, 21, 9, 0)

        item.complete(actor_id=counterpart, now=now)

        assert item.is_completed is True

    def test_non_counterpart_cannot_complete(self) -> None:
        counterpart = UserId.generate()
        other = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)

        with pytest.raises(PermissionError, match="Only the counterpart"):
            item.complete(actor_id=other, now=datetime(2026, 3, 21, 9, 0))

    def test_cannot_complete_twice(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        item.complete(actor_id=counterpart, now=datetime(2026, 3, 21, 9, 0))

        with pytest.raises(ValueError, match="already completed"):
            item.complete(actor_id=counterpart, now=datetime(2026, 3, 21, 10, 0))

    def test_emits_action_item_completed_event(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        now = datetime(2026, 3, 21, 9, 0)

        item.complete(actor_id=counterpart, now=now)

        completed_events = [
            e for e in item.events if isinstance(e, ActionItemCompleted)
        ]
        assert len(completed_events) == 1
        assert completed_events[0].completed_at == now
        assert completed_events[0].counterpart_id == counterpart
