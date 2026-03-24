"""Tests for CompleteActionItemUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.complete_action_item import (
    ActionItemNotFoundError,
    CompleteActionItemInput,
    CompleteActionItemOutput,
    CompleteActionItemUseCase,
)
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.events import ActionItemCompleted
from contexts.record.domain.exceptions import (
    ActionItemAlreadyCompletedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle, RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryActionItemRepository,
    SpyEventDispatcher,
)


def _make_action_item(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    record_id: RecordId | None = None,
) -> ActionItem:
    org = organizer_id or UserId.generate()
    return ActionItem.create(
        counterpart_id=counterpart_id or UserId.generate(),
        record_id=record_id or RecordId.generate(),
        title=ActionItemTitle("Follow up on project status"),
        actor_id=org,
        organizer_id=org,
        now=datetime(2026, 3, 20, 10, 30),
    )


def _build_use_case(
    *,
    action_item_repo: InMemoryActionItemRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    CompleteActionItemUseCase,
    InMemoryActionItemRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    air = action_item_repo or InMemoryActionItemRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = CompleteActionItemUseCase(
        action_item_repository=air,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, air, u, ed


class TestCompleteActionItem:
    """Tests for successful action item completion."""

    async def test_counterpart_can_complete_action_item(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        uc, air, _uow, _ed = _build_use_case()
        await air.save(item)
        item.collect_events()  # clear creation event

        output = await uc.execute(
            CompleteActionItemInput(
                action_item_id=item.id,
                actor_id=counterpart,
            )
        )

        assert isinstance(output, CompleteActionItemOutput)
        assert output.action_item_id == item.id
        saved = await air.get_by_id(item.id)
        assert saved is not None
        assert saved.is_completed is True

    async def test_commits_transaction(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        uc, air, uow, _ed = _build_use_case()
        await air.save(item)
        item.collect_events()

        await uc.execute(
            CompleteActionItemInput(
                action_item_id=item.id,
                actor_id=counterpart,
            )
        )

        assert uow.committed is True

    async def test_dispatches_action_item_completed_event(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        uc, air, _uow, ed = _build_use_case()
        await air.save(item)
        item.collect_events()  # clear creation event

        await uc.execute(
            CompleteActionItemInput(
                action_item_id=item.id,
                actor_id=counterpart,
            )
        )

        completed_events = [
            e for e in ed.dispatched_events if isinstance(e, ActionItemCompleted)
        ]
        assert len(completed_events) == 1
        event = completed_events[0]
        assert event.action_item_id == item.id
        assert event.counterpart_id == counterpart


class TestCompleteActionItemErrors:
    """Tests for error conditions."""

    async def test_raises_when_action_item_not_found(self) -> None:
        uc, _air, _uow, _ed = _build_use_case()

        with pytest.raises(ActionItemNotFoundError):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=ActionItemId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_is_not_counterpart(self) -> None:
        counterpart = UserId.generate()
        organizer = UserId.generate()
        item = _make_action_item(organizer_id=organizer, counterpart_id=counterpart)
        uc, air, _uow, _ed = _build_use_case()
        await air.save(item)
        item.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the counterpart"):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=item.id,
                    actor_id=organizer,
                )
            )

    async def test_raises_when_already_completed(self) -> None:
        counterpart = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        item.complete(actor_id=counterpart, now=datetime(2026, 3, 21, 9, 0))
        uc, air, _uow, _ed = _build_use_case()
        await air.save(item)
        item.collect_events()

        with pytest.raises(ActionItemAlreadyCompletedError, match="already completed"):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=item.id,
                    actor_id=counterpart,
                )
            )

    async def test_raises_when_third_party_tries_to_complete(self) -> None:
        counterpart = UserId.generate()
        third_party = UserId.generate()
        item = _make_action_item(counterpart_id=counterpart)
        uc, air, _uow, _ed = _build_use_case()
        await air.save(item)
        item.collect_events()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=item.id,
                    actor_id=third_party,
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _air, uow, _ed = _build_use_case()

        with pytest.raises(ActionItemNotFoundError):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=ActionItemId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _air, _uow, ed = _build_use_case()

        with pytest.raises(ActionItemNotFoundError):
            await uc.execute(
                CompleteActionItemInput(
                    action_item_id=ActionItemId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert ed.dispatched_events == []
