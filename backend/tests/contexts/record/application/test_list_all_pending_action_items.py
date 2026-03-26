"""Tests for ListAllPendingActionItemsService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.record.application.list_all_pending_action_items import (
    MAX_LIMIT,
    InvalidLimitError,
    ListAllPendingActionItemsInput,
    ListAllPendingActionItemsOutput,
    ListAllPendingActionItemsService,
)
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ActionItemTitle, RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    InMemoryActionItemRepository,
    InMemoryRecordRepository,
)


def _make_record(
    *,
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
    conducted_at: datetime | None = None,
    now: datetime | None = None,
) -> Record:
    record = Record.create(
        organizer_id=organizer or UserId.generate(),
        counterpart_id=counterpart or UserId.generate(),
        conducted_at=conducted_at or datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        now=now,
    )
    record.collect_events()
    return record


def _make_action_item(
    *,
    counterpart: UserId,
    record_id: RecordId,
    organizer: UserId,
    title: str = "Follow up",
    now: datetime | None = None,
) -> ActionItem:
    item = ActionItem.create(
        counterpart_id=counterpart,
        record_id=record_id,
        title=ActionItemTitle(title),
        actor_id=organizer,
        organizer_id=organizer,
        now=now,
    )
    item.collect_events()
    return item


def _build_service(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    action_item_repo: InMemoryActionItemRepository | None = None,
) -> tuple[
    ListAllPendingActionItemsService,
    InMemoryRecordRepository,
    InMemoryActionItemRepository,
]:
    rr = record_repo or InMemoryRecordRepository()
    air = action_item_repo or InMemoryActionItemRepository()
    svc = ListAllPendingActionItemsService(
        action_item_repository=air,
        record_repository=rr,
    )
    return svc, rr, air


class TestListAllPendingActionItems:
    """Tests for successful all-pending action item retrieval."""

    async def test_returns_pending_items_for_organizer(self) -> None:
        """Basic retrieval of pending action items across all counterparts."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)
        item = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Review document",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        air.set_organizer_map(record.id, organizer)
        await air.save(item)

        output = await svc.execute(ListAllPendingActionItemsInput(actor_id=organizer))

        assert isinstance(output, ListAllPendingActionItemsOutput)
        assert len(output.items) == 1
        dto = output.items[0]
        assert dto.action_item_id == item.id
        assert dto.content == "Review document"
        assert dto.record_id == record.id
        assert dto.counterpart_id == counterpart
        assert dto.conducted_at == record.conducted_at

    async def test_returns_items_from_multiple_counterparts(self) -> None:
        """Items from different counterparts are aggregated."""
        organizer = UserId.generate()
        counterpart_a = UserId.generate()
        counterpart_b = UserId.generate()

        record_a = _make_record(
            organizer=organizer,
            counterpart=counterpart_a,
            conducted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        )
        record_b = _make_record(
            organizer=organizer,
            counterpart=counterpart_b,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        item_a = _make_action_item(
            counterpart=counterpart_a,
            record_id=record_a.id,
            organizer=organizer,
            title="Task for A",
            now=datetime(2026, 2, 1, 11, 0, tzinfo=UTC),
        )
        item_b = _make_action_item(
            counterpart=counterpart_b,
            record_id=record_b.id,
            organizer=organizer,
            title="Task for B",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record_a)
        await rr.save(record_b)
        air.set_organizer_map(record_a.id, organizer)
        air.set_organizer_map(record_b.id, organizer)
        await air.save(item_a)
        await air.save(item_b)

        output = await svc.execute(ListAllPendingActionItemsInput(actor_id=organizer))

        assert len(output.items) == 2
        contents = {dto.content for dto in output.items}
        assert contents == {"Task for A", "Task for B"}

    async def test_excludes_completed_items(self) -> None:
        """Completed action items are not returned."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        pending = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Pending task",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )
        completed = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Done task",
            now=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
        )
        completed.complete(
            actor_id=counterpart,
            now=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        )
        completed.collect_events()

        svc, rr, air = _build_service()
        await rr.save(record)
        air.set_organizer_map(record.id, organizer)
        await air.save(pending)
        await air.save(completed)

        output = await svc.execute(ListAllPendingActionItemsInput(actor_id=organizer))

        assert len(output.items) == 1
        assert output.items[0].content == "Pending task"

    async def test_excludes_items_from_other_organizers(self) -> None:
        """Items from other organizers' records are not returned."""
        organizer_a = UserId.generate()
        organizer_b = UserId.generate()
        counterpart = UserId.generate()

        record_a = _make_record(organizer=organizer_a, counterpart=counterpart)
        record_b = _make_record(organizer=organizer_b, counterpart=counterpart)

        item_a = _make_action_item(
            counterpart=counterpart,
            record_id=record_a.id,
            organizer=organizer_a,
            title="A's task",
        )
        item_b = _make_action_item(
            counterpart=counterpart,
            record_id=record_b.id,
            organizer=organizer_b,
            title="B's task",
        )

        svc, rr, air = _build_service()
        await rr.save(record_a)
        await rr.save(record_b)
        air.set_organizer_map(record_a.id, organizer_a)
        air.set_organizer_map(record_b.id, organizer_b)
        await air.save(item_a)
        await air.save(item_b)

        output = await svc.execute(ListAllPendingActionItemsInput(actor_id=organizer_a))

        assert len(output.items) == 1
        assert output.items[0].content == "A's task"

    async def test_respects_limit(self) -> None:
        """Only up to limit items are returned."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        svc, rr, air = _build_service()
        await rr.save(record)
        air.set_organizer_map(record.id, organizer)

        for i in range(5):
            item = _make_action_item(
                counterpart=counterpart,
                record_id=record.id,
                organizer=organizer,
                title=f"Task {i}",
                now=datetime(2026, 1, 1 + i, 10, 0, tzinfo=UTC),
            )
            await air.save(item)

        output = await svc.execute(
            ListAllPendingActionItemsInput(
                actor_id=organizer,
                limit=3,
            )
        )

        assert len(output.items) == 3
        assert output.items[0].content == "Task 0"
        assert output.items[1].content == "Task 1"
        assert output.items[2].content == "Task 2"

    async def test_returns_empty_when_no_pending_items(self) -> None:
        """Returns empty list when organizer has no pending items."""
        organizer = UserId.generate()

        svc, _rr, _air = _build_service()

        output = await svc.execute(ListAllPendingActionItemsInput(actor_id=organizer))

        assert output.items == []

    async def test_default_limit_is_50(self) -> None:
        """Default limit should be 50."""
        input_dto = ListAllPendingActionItemsInput(
            actor_id=UserId.generate(),
        )
        assert input_dto.limit == 50


class TestListAllPendingActionItemsLimitValidation:
    """Tests for limit parameter validation."""

    async def test_limit_zero_raises(self) -> None:
        """limit=0 is rejected."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListAllPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    limit=0,
                )
            )

    async def test_limit_negative_raises(self) -> None:
        """limit=-1 is rejected."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListAllPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    limit=-1,
                )
            )

    async def test_limit_exceeds_max_raises(self) -> None:
        """limit above MAX_LIMIT is rejected."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListAllPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    limit=MAX_LIMIT + 1,
                )
            )
