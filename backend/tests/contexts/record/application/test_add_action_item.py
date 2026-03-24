"""Tests for AddActionItemUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.add_action_item import (
    AddActionItemInput,
    AddActionItemOutput,
    AddActionItemUseCase,
    RecordNotFoundError,
)
from contexts.record.domain.events import ActionItemAdded
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ActionItemTitle, RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryActionItemRepository,
    InMemoryRecordRepository,
    SpyEventDispatcher,
)


def _make_draft_record(
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
) -> Record:
    return Record.create(
        organizer_id=organizer or UserId.generate(),
        counterpart_id=counterpart or UserId.generate(),
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )


def _build_use_case(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    action_item_repo: InMemoryActionItemRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    AddActionItemUseCase,
    InMemoryRecordRepository,
    InMemoryActionItemRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    air = action_item_repo or InMemoryActionItemRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = AddActionItemUseCase(
        record_repository=rr,
        action_item_repository=air,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, air, u, ed


class TestAddActionItem:
    """Tests for successful action item addition."""

    async def test_creates_action_item_linked_to_counterpart(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, air, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            AddActionItemInput(
                record_id=record.id,
                actor_id=organizer,
                title=ActionItemTitle("Follow up on project status"),
            )
        )

        assert isinstance(output, AddActionItemOutput)
        saved_items = air.saved_items
        assert len(saved_items) == 1
        item = saved_items[0]
        assert item.id == output.action_item_id
        assert item.counterpart_id == counterpart
        assert item.record_id == record.id
        assert item.title.value == "Follow up on project status"
        assert item.is_completed is False

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _air, uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            AddActionItemInput(
                record_id=record.id,
                actor_id=organizer,
                title=ActionItemTitle("Task"),
            )
        )

        assert uow.committed is True

    async def test_dispatches_action_item_added_event(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _air, _uow, ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            AddActionItemInput(
                record_id=record.id,
                actor_id=organizer,
                title=ActionItemTitle("Review document"),
            )
        )

        added_events = [
            e for e in ed.dispatched_events if isinstance(e, ActionItemAdded)
        ]
        assert len(added_events) == 1
        event = added_events[0]
        assert event.action_item_id == output.action_item_id
        assert event.counterpart_id == counterpart
        assert event.record_id == record.id
        assert event.title == "Review document"


class TestAddActionItemErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _air, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddActionItemInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    title=ActionItemTitle("Task"),
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _air, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                AddActionItemInput(
                    record_id=record.id,
                    actor_id=counterpart,
                    title=ActionItemTitle("Unauthorized task"),
                )
            )

    async def test_raises_when_viewer_tries_to_add(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _air, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                AddActionItemInput(
                    record_id=record.id,
                    actor_id=viewer,
                    title=ActionItemTitle("Unauthorized task"),
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, _air, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddActionItemInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    title=ActionItemTitle("Task"),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _air, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddActionItemInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    title=ActionItemTitle("Task"),
                )
            )

        assert ed.dispatched_events == []
