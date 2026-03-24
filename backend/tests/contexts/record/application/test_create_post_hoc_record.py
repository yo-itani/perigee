"""Tests for CreatePostHocRecordUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordInput,
    CreatePostHocRecordUseCase,
    SameUserError,
)
from contexts.record.domain.events import RecordCreated
from contexts.record.domain.value_objects import RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryRecordRepository,
    SpyEventDispatcher,
)


def _build_use_case(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    CreatePostHocRecordUseCase,
    InMemoryRecordRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = CreatePostHocRecordUseCase(
        record_repository=rr,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, u, ed


class TestCreatePostHocRecord:
    """Tests for successful post-hoc record creation."""

    async def test_creates_draft_record_without_schedule(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        conducted_at = datetime(2026, 3, 25, 10, 30)
        uc, rr, _uow, _ed = _build_use_case()

        output = await uc.execute(
            CreatePostHocRecordInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                conducted_at=conducted_at,
            )
        )

        saved = rr.saved_records
        assert len(saved) == 1
        record = saved[0]
        assert record.id == output.record_id
        assert record.status == RecordStatus.DRAFT
        assert record.organizer_id == organizer
        assert record.counterpart_id == counterpart
        assert record.schedule_id is None
        assert record.conducted_at == conducted_at

    async def test_commits_transaction(self) -> None:
        uc, _rr, uow, _ed = _build_use_case()

        await uc.execute(
            CreatePostHocRecordInput(
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
                conducted_at=datetime(2026, 3, 25, 10, 30),
            )
        )

        assert uow.committed is True

    async def test_dispatches_record_created_event_after_commit(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        uc, _rr, _uow, ed = _build_use_case()

        output = await uc.execute(
            CreatePostHocRecordInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                conducted_at=datetime(2026, 3, 25, 10, 30),
            )
        )

        record_created_events = [
            e for e in ed.dispatched_events if isinstance(e, RecordCreated)
        ]
        assert len(record_created_events) == 1
        event = record_created_events[0]
        assert event.record_id == output.record_id
        assert event.organizer_id == organizer
        assert event.counterpart_id == counterpart
        assert event.schedule_id is None

    async def test_conducted_at_is_preserved(self) -> None:
        conducted_at = datetime(2026, 1, 15, 14, 0)
        uc, rr, _uow, _ed = _build_use_case()

        await uc.execute(
            CreatePostHocRecordInput(
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
                conducted_at=conducted_at,
            )
        )

        record = rr.saved_records[0]
        assert record.conducted_at == conducted_at


class TestCreatePostHocRecordErrors:
    """Tests for error conditions."""

    async def test_raises_when_organizer_equals_counterpart(self) -> None:
        same_user = UserId.generate()
        uc, _rr, _uow, _ed = _build_use_case()

        with pytest.raises(SameUserError):
            await uc.execute(
                CreatePostHocRecordInput(
                    organizer_id=same_user,
                    counterpart_id=same_user,
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

    async def test_does_not_commit_when_same_user(self) -> None:
        same_user = UserId.generate()
        uc, _rr, uow, _ed = _build_use_case()

        with pytest.raises(SameUserError):
            await uc.execute(
                CreatePostHocRecordInput(
                    organizer_id=same_user,
                    counterpart_id=same_user,
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_when_same_user(self) -> None:
        same_user = UserId.generate()
        uc, _rr, _uow, ed = _build_use_case()

        with pytest.raises(SameUserError):
            await uc.execute(
                CreatePostHocRecordInput(
                    organizer_id=same_user,
                    counterpart_id=same_user,
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

        assert ed.dispatched_events == []
