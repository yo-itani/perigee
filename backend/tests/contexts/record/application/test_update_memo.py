"""Tests for UpdateMemoUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.update_memo import (
    RecordNotFoundError,
    UpdateMemoInput,
    UpdateMemoOutput,
    UpdateMemoUseCase,
)
from contexts.record.domain.events import MemoUpdated
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId, RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
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
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    UpdateMemoUseCase,
    InMemoryRecordRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = UpdateMemoUseCase(
        record_repository=rr,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, u, ed


class TestUpdateMemo:
    """Tests for successful memo update."""

    async def test_updates_memo_content(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()  # Clear creation events

        output = await uc.execute(
            UpdateMemoInput(
                record_id=record.id,
                actor_id=organizer,
                memo=Memo("New memo content"),
            )
        )

        assert isinstance(output, UpdateMemoOutput)
        assert output.record_id == record.id
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert saved.memo.value == "New memo content"

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            UpdateMemoInput(
                record_id=record.id,
                actor_id=organizer,
                memo=Memo("Updated"),
            )
        )

        assert uow.committed is True

    async def test_dispatches_memo_updated_event(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            UpdateMemoInput(
                record_id=record.id,
                actor_id=organizer,
                memo=Memo("Event test"),
            )
        )

        memo_events = [e for e in ed.dispatched_events if isinstance(e, MemoUpdated)]
        assert len(memo_events) == 1
        assert memo_events[0].record_id == record.id
        assert memo_events[0].organizer_id == organizer

    async def test_record_status_remains_draft(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            UpdateMemoInput(
                record_id=record.id,
                actor_id=organizer,
                memo=Memo("Still draft"),
            )
        )

        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert saved.status == RecordStatus.DRAFT


class TestUpdateMemoErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                UpdateMemoInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    memo=Memo("Test"),
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        organizer = UserId.generate()
        other_user = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                UpdateMemoInput(
                    record_id=record.id,
                    actor_id=other_user,
                    memo=Memo("Unauthorized"),
                )
            )

    async def test_raises_when_record_is_published(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 25, 12, 0))
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(RecordAlreadyPublishedError):
            await uc.execute(
                UpdateMemoInput(
                    record_id=record.id,
                    actor_id=organizer,
                    memo=Memo("Too late"),
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                UpdateMemoInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    memo=Memo("Test"),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                UpdateMemoInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    memo=Memo("Test"),
                )
            )

        assert ed.dispatched_events == []
