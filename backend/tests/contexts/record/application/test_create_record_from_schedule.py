"""Tests for CreateRecordFromScheduleUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId, ScheduleStatus
from contexts.record.application.create_record_from_schedule import (
    CreateRecordFromScheduleInput,
    CreateRecordFromScheduleUseCase,
    ScheduleCancelledError,
    ScheduleNotFoundError,
)
from contexts.record.domain.events import RecordCreated
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.value_objects import RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryRecordRepository,
    InMemoryScheduleRepository,
    SpyEventDispatcher,
)


def _make_confirmed_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    now: datetime | None = None,
) -> Schedule:
    """Create a confirmed schedule for testing."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    ts = now or datetime(2026, 3, 20, 9, 0)
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=datetime(2026, 3, 25, 10, 0),
        requested_by=org,
        title=ScheduleTitle("Weekly 1on1"),
        now=ts,
    )
    schedule.confirm(actor_id=cp, now=ts)
    schedule.collect_events()  # clear creation/confirmation events
    return schedule


def _make_requested_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    now: datetime | None = None,
) -> Schedule:
    """Create a schedule still in Requested status."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    ts = now or datetime(2026, 3, 20, 9, 0)
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=datetime(2026, 3, 25, 10, 0),
        requested_by=org,
        title=ScheduleTitle("Weekly 1on1"),
        now=ts,
    )
    schedule.collect_events()  # clear creation events
    return schedule


def _make_cancelled_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
) -> Schedule:
    """Create a cancelled schedule."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    ts = datetime(2026, 3, 20, 9, 0)
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=datetime(2026, 3, 25, 10, 0),
        requested_by=org,
        title=ScheduleTitle("Weekly 1on1"),
        now=ts,
    )
    schedule.cancel(actor_id=org, now=ts)
    schedule.collect_events()
    return schedule


def _build_use_case(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    schedule_repo: InMemoryScheduleRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    CreateRecordFromScheduleUseCase,
    InMemoryRecordRepository,
    InMemoryScheduleRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    sr = schedule_repo or InMemoryScheduleRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = CreateRecordFromScheduleUseCase(
        record_repository=rr,
        schedule_repository=sr,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, sr, u, ed


class TestCreateRecordFromSchedule:
    """Tests for successful record creation from a confirmed schedule."""

    async def test_creates_draft_record_linked_to_schedule(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, rr, sr, uow, ed = _build_use_case()
        sr.add(schedule)
        conducted_at = datetime(2026, 3, 25, 10, 30)

        output = await uc.execute(
            CreateRecordFromScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
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
        assert record.schedule_id == schedule.id
        assert record.conducted_at == conducted_at

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, _rr, sr, uow, _ed = _build_use_case()
        sr.add(schedule)

        await uc.execute(
            CreateRecordFromScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                conducted_at=datetime(2026, 3, 25, 10, 30),
            )
        )

        assert uow.committed is True

    async def test_dispatches_record_created_event_after_commit(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, _rr, sr, _uow, ed = _build_use_case()
        sr.add(schedule)

        output = await uc.execute(
            CreateRecordFromScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                conducted_at=datetime(2026, 3, 25, 10, 30),
            )
        )

        record_created_events = [
            e for e in ed.dispatched_events if isinstance(e, RecordCreated)
        ]
        assert len(record_created_events) == 1
        assert record_created_events[0].record_id == output.record_id
        assert record_created_events[0].schedule_id == schedule.id

    async def test_created_at_uses_current_time_not_conducted_at(self) -> None:
        """created_at should reflect current time, not the conducted_at value."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, rr, sr, _uow, _ed = _build_use_case()
        sr.add(schedule)
        past_conducted_at = datetime(2025, 6, 1, 10, 0)
        before = datetime.now(UTC)

        await uc.execute(
            CreateRecordFromScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                conducted_at=past_conducted_at,
            )
        )

        after = datetime.now(UTC)
        record = rr.saved_records[0]
        assert record.conducted_at == past_conducted_at
        # created_at should be around "now", not the past conducted_at
        tolerance = timedelta(seconds=1)
        assert before - tolerance <= record.created_at <= after + tolerance

    async def test_auto_confirms_requested_schedule(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_requested_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        assert schedule.status == ScheduleStatus.REQUESTED
        uc, _rr, sr, _uow, _ed = _build_use_case()
        sr.add(schedule)

        await uc.execute(
            CreateRecordFromScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                conducted_at=datetime(2026, 3, 25, 10, 30),
            )
        )

        assert schedule.status == ScheduleStatus.CONFIRMED


class TestCreateRecordFromScheduleErrors:
    """Tests for error conditions."""

    async def test_raises_when_schedule_not_found(self) -> None:
        uc, _rr, _sr, _uow, _ed = _build_use_case()
        fake_id = ScheduleId.generate()

        with pytest.raises(ScheduleNotFoundError):
            await uc.execute(
                CreateRecordFromScheduleInput(
                    schedule_id=fake_id,
                    actor_id=UserId.generate(),
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

    async def test_raises_when_schedule_is_cancelled(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_cancelled_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, _rr, sr, _uow, _ed = _build_use_case()
        sr.add(schedule)

        with pytest.raises(ScheduleCancelledError):
            await uc.execute(
                CreateRecordFromScheduleInput(
                    schedule_id=schedule.id,
                    actor_id=organizer,
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(
            organizer_id=organizer, counterpart_id=counterpart
        )
        uc, _rr, sr, _uow, _ed = _build_use_case()
        sr.add(schedule)

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                CreateRecordFromScheduleInput(
                    schedule_id=schedule.id,
                    actor_id=counterpart,
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, _sr, uow, _ed = _build_use_case()
        fake_id = ScheduleId.generate()

        with pytest.raises(ScheduleNotFoundError):
            await uc.execute(
                CreateRecordFromScheduleInput(
                    schedule_id=fake_id,
                    actor_id=UserId.generate(),
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _sr, _uow, ed = _build_use_case()
        fake_id = ScheduleId.generate()

        with pytest.raises(ScheduleNotFoundError):
            await uc.execute(
                CreateRecordFromScheduleInput(
                    schedule_id=fake_id,
                    actor_id=UserId.generate(),
                    conducted_at=datetime(2026, 3, 25, 10, 30),
                )
            )

        assert ed.dispatched_events == []
