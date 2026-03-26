"""Tests for ListPendingActionItemsQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.record.application.list_pending_action_items import (
    MAX_LIMIT,
    InvalidLimitError,
    ListPendingActionItemsInput,
    ListPendingActionItemsOutput,
    ListPendingActionItemsQueryService,
)
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.exceptions import UnauthorizedOperationError
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
    ListPendingActionItemsQueryService,
    InMemoryRecordRepository,
    InMemoryActionItemRepository,
]:
    rr = record_repo or InMemoryRecordRepository()
    air = action_item_repo or InMemoryActionItemRepository()
    svc = ListPendingActionItemsQueryService(
        action_item_repository=air,
        record_repository=rr,
    )
    return svc, rr, air


class TestListPendingActionItems:
    """Tests for successful pending action item retrieval."""

    async def test_returns_pending_items_for_counterpart(self) -> None:
        """Basic retrieval of pending action items."""
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
        await air.save(item)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert isinstance(output, ListPendingActionItemsOutput)
        assert len(output.items) == 1
        dto = output.items[0]
        assert dto.action_item_id == item.id
        assert dto.content == "Review document"
        assert dto.record_id == record.id
        assert dto.organizer_id == organizer
        assert dto.conducted_at == record.conducted_at

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
        await air.save(pending)
        await air.save(completed)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items) == 1
        assert output.items[0].content == "Pending task"

    async def test_returns_items_ordered_by_created_at_ascending(self) -> None:
        """Items are returned oldest first."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        item_old = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Old task",
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        item_new = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="New task",
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        # Save in reverse order to verify sorting
        await air.save(item_new)
        await air.save(item_old)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items) == 2
        assert output.items[0].content == "Old task"
        assert output.items[1].content == "New task"

    async def test_respects_limit(self) -> None:
        """Only up to limit items are returned."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        svc, rr, air = _build_service()
        await rr.save(record)

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
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
                limit=3,
            )
        )

        assert len(output.items) == 3
        # Should be the 3 oldest
        assert output.items[0].content == "Task 0"
        assert output.items[1].content == "Task 1"
        assert output.items[2].content == "Task 2"

    async def test_default_limit_is_50(self) -> None:
        """Default limit should be 50."""
        input_dto = ListPendingActionItemsInput(
            actor_id=UserId.generate(),
            counterpart_id=UserId.generate(),
        )
        assert input_dto.limit == 50

    async def test_counterpart_can_query_own_items(self) -> None:
        """The counterpart themselves can query their own pending items."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)
        item = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Self check",
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        await air.save(item)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=counterpart,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items) == 1
        assert output.items[0].content == "Self check"

    async def test_includes_items_from_multiple_records(self) -> None:
        """Items from different records with the same counterpart are aggregated."""
        organizer_a = UserId.generate()
        organizer_b = UserId.generate()
        counterpart = UserId.generate()

        record_a = _make_record(
            organizer=organizer_a,
            counterpart=counterpart,
            conducted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        )
        record_b = _make_record(
            organizer=organizer_b,
            counterpart=counterpart,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        item_a = _make_action_item(
            counterpart=counterpart,
            record_id=record_a.id,
            organizer=organizer_a,
            title="From record A",
            now=datetime(2026, 2, 1, 11, 0, tzinfo=UTC),
        )
        item_b = _make_action_item(
            counterpart=counterpart,
            record_id=record_b.id,
            organizer=organizer_b,
            title="From record B",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record_a)
        await rr.save(record_b)
        await air.save(item_a)
        await air.save(item_b)

        # organizer_a can see all items for this counterpart
        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer_a,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items) == 2
        contents = {dto.content for dto in output.items}
        assert contents == {"From record A", "From record B"}

    async def test_each_item_includes_record_info(self) -> None:
        """Each DTO contains the originating Record's info."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        conducted = datetime(2026, 3, 15, 14, 0, tzinfo=UTC)
        record = _make_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=conducted,
        )
        item = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Check status",
            now=datetime(2026, 3, 15, 15, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        await air.save(item)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
            )
        )

        dto = output.items[0]
        assert dto.record_id == record.id
        assert dto.organizer_id == organizer
        assert dto.conducted_at == conducted
        assert dto.created_at == datetime(2026, 3, 15, 15, 0, tzinfo=UTC)

    async def test_returns_empty_when_no_pending_items(self) -> None:
        """Returns empty list when counterpart has no pending items."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.items == []


class TestListPendingActionItemsAuthorization:
    """Tests for authorization checks."""

    async def test_raises_when_actor_not_involved(self) -> None:
        """Unrelated user cannot query pending items."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        with pytest.raises(UnauthorizedOperationError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=outsider,
                    counterpart_id=counterpart,
                )
            )

    async def test_raises_when_no_records_exist(self) -> None:
        """No records at all means no access."""
        svc, _rr, _air = _build_service()

        with pytest.raises(UnauthorizedOperationError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                )
            )

    async def test_organizer_of_different_counterpart_cannot_access(self) -> None:
        """An organizer with records for a different counterpart is denied."""
        organizer = UserId.generate()
        counterpart_a = UserId.generate()
        counterpart_b = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart_a)

        svc, rr, _air = _build_service()
        await rr.save(record)

        with pytest.raises(UnauthorizedOperationError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=organizer,
                    counterpart_id=counterpart_b,
                )
            )


class TestListPendingActionItemsLimitValidation:
    """Tests for limit parameter validation."""

    async def test_limit_zero_raises(self) -> None:
        """limit=0 is rejected before any repository call."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    limit=0,
                )
            )

    async def test_limit_negative_raises(self) -> None:
        """limit=-1 is rejected."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    limit=-1,
                )
            )

    async def test_limit_exceeds_max_raises(self) -> None:
        """limit above MAX_LIMIT is rejected."""
        svc, _rr, _air = _build_service()

        with pytest.raises(InvalidLimitError):
            await svc.execute(
                ListPendingActionItemsInput(
                    actor_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    limit=MAX_LIMIT + 1,
                )
            )

    async def test_limit_at_max_is_accepted(self) -> None:
        """limit=MAX_LIMIT is valid (boundary)."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
                limit=MAX_LIMIT,
            )
        )

        assert output.items == []

    async def test_limit_one_is_accepted(self) -> None:
        """limit=1 is the minimum valid value."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer=organizer, counterpart=counterpart)
        item = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Single item",
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        await air.save(item)

        output = await svc.execute(
            ListPendingActionItemsInput(
                actor_id=organizer,
                counterpart_id=counterpart,
                limit=1,
            )
        )

        assert len(output.items) == 1
