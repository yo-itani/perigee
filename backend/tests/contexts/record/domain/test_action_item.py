from datetime import datetime

import pytest

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.events import ActionItemAdded, ActionItemCompleted
from contexts.record.domain.exceptions import (
    ActionItemAlreadyCompletedError,
    InvalidActionItemTitleError,
    UnauthorizedOperationError,
)
from contexts.record.domain.value_objects import ActionItemTitle, RecordId
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
        assert item.title == ActionItemTitle("Follow up on project status")

    def test_only_organizer_can_create(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="Task",
                actor_id=other,
                organizer_id=organizer,
            )

    def test_title_must_not_be_empty(self) -> None:
        organizer = UserId.generate()

        with pytest.raises(InvalidActionItemTitleError, match="must not be empty"):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="   ",
                actor_id=organizer,
                organizer_id=organizer,
            )

    def test_title_must_not_contain_newlines(self) -> None:
        organizer = UserId.generate()

        with pytest.raises(
            InvalidActionItemTitleError, match="must not contain newlines"
        ):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="line1\nline2",
                actor_id=organizer,
                organizer_id=organizer,
            )

    def test_title_must_not_exceed_max_length(self) -> None:
        organizer = UserId.generate()

        with pytest.raises(InvalidActionItemTitleError, match="must not exceed"):
            ActionItem.create(
                counterpart_id=UserId.generate(),
                record_id=RecordId.generate(),
                title="a" * 201,
                actor_id=organizer,
                organizer_id=organizer,
            )

    def test_title_strips_whitespace(self) -> None:
        item = _make_action_item(title="  some task  ")
        assert item.title.value == "some task"

    def test_emits_action_item_added_event(self) -> None:
        item = _make_action_item()
        events = item.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ActionItemAdded)
        assert event.action_item_id == item.id
        assert event.title == item.title.value

    def test_collect_events_clears_list(self) -> None:
        item = _make_action_item()
        events = item.collect_events()
        assert len(events) == 1
        assert item.collect_events() == []


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

        with pytest.raises(UnauthorizedOperationError, match="Only the counterpart"):
            item.complete(actor_id=other, now=datetime(2026, 3, 21, 9, 0))

    def test_cannot_complete_twice(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        item.complete(actor_id=counterpart, now=datetime(2026, 3, 21, 9, 0))

        with pytest.raises(ActionItemAlreadyCompletedError, match="already completed"):
            item.complete(actor_id=counterpart, now=datetime(2026, 3, 21, 10, 0))

    def test_emits_action_item_completed_event(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        item.collect_events()  # clear creation event
        now = datetime(2026, 3, 21, 9, 0)

        item.complete(actor_id=counterpart, now=now)

        events = item.collect_events()
        completed_events = [e for e in events if isinstance(e, ActionItemCompleted)]
        assert len(completed_events) == 1
        assert completed_events[0].completed_at == now
        assert completed_events[0].counterpart_id == counterpart
