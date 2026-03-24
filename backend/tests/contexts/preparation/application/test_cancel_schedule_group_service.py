"""Tests for CancelScheduleGroupService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.cancel_schedule_group_service import (
    CancelScheduleGroupService,
)
from contexts.preparation.domain.events import ScheduleCancelled
from contexts.preparation.domain.exceptions import (
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleStatus
from foundation.domain.exceptions import EntityNotFoundError
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


def _create_group_with_schedules(
    organizer: UserId,
    counterpart_ids: list[UserId],
    now: datetime,
) -> tuple[ScheduleGroup, list[Schedule]]:
    """Helper: create a group and its schedules."""
    group = ScheduleGroup.create(
        organizer_id=organizer,
        title=ScheduleTitle("Test Group"),
        now=now,
    )
    schedules: list[Schedule] = []
    for i, cp_id in enumerate(counterpart_ids):
        schedule = Schedule.create(
            organizer_id=organizer,
            counterpart_id=cp_id,
            scheduled_at=now + timedelta(days=1 + i),
            requested_by=organizer,
            title=ScheduleTitle("Test Group"),
            schedule_group_id=group.id,
            now=now,
        )
        group.register_schedule(schedule.id)
        schedules.append(schedule)

    # Drain factory events so they don't interfere with test assertions
    group.collect_events()
    for s in schedules:
        s.collect_events()

    return group, schedules


class TestCancelScheduleGroup:
    """Cancel all schedules in a ScheduleGroup."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CancelScheduleGroupService:
        return CancelScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_cancels_all_schedules(
        self,
        service: CancelScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """All schedules in the group are cancelled."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group, schedules = _create_group_with_schedules(
            organizer, [UserId.generate(), UserId.generate()], now
        )
        await schedule_group_repo.save(group)
        for s in schedules:
            await schedule_repo.save(s)

        await service.execute(
            schedule_group_id=group.id,
            actor_id=organizer,
        )

        for s_id in group.schedule_ids:
            schedule = await schedule_repo.get_by_id(s_id)
            assert schedule is not None
            assert schedule.status == ScheduleStatus.CANCELLED

    async def test_dispatches_cancelled_events(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleCancelled for each schedule."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCancelled, capture)  # type: ignore[arg-type]

        service = CancelScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        now = datetime.now(UTC)
        group, schedules = _create_group_with_schedules(
            organizer, [UserId.generate(), UserId.generate()], now
        )
        await schedule_group_repo.save(group)
        for s in schedules:
            await schedule_repo.save(s)

        await service.execute(schedule_group_id=group.id, actor_id=organizer)

        assert len(dispatched) == 2
        assert all(isinstance(e, ScheduleCancelled) for e in dispatched)

    async def test_rejects_non_organizer(
        self,
        service: CancelScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedScheduleGroupOperationError for non-organizer."""
        organizer = UserId.generate()
        other_user = UserId.generate()
        now = datetime.now(UTC)
        group, schedules = _create_group_with_schedules(
            organizer, [UserId.generate()], now
        )
        await schedule_group_repo.save(group)
        for s in schedules:
            await schedule_repo.save(s)

        with pytest.raises(UnauthorizedScheduleGroupOperationError):
            await service.execute(
                schedule_group_id=group.id,
                actor_id=other_user,
            )

    async def test_raises_not_found(
        self,
        service: CancelScheduleGroupService,
    ) -> None:
        """Raises EntityNotFoundError for nonexistent group."""
        with pytest.raises(EntityNotFoundError):
            await service.execute(
                schedule_group_id=ScheduleGroupId.generate(),
                actor_id=UserId.generate(),
            )

    async def test_all_or_nothing_on_already_cancelled(
        self,
        service: CancelScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """If any schedule is already cancelled, the entire operation fails."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group, schedules = _create_group_with_schedules(
            organizer, [UserId.generate(), UserId.generate()], now
        )
        # Cancel the first schedule manually
        schedules[0].cancel(actor_id=organizer, now=now)
        schedules[0].collect_events()

        await schedule_group_repo.save(group)
        for s in schedules:
            await schedule_repo.save(s)

        with pytest.raises(ScheduleAlreadyCancelledError):
            await service.execute(
                schedule_group_id=group.id,
                actor_id=organizer,
            )

        # Second schedule should NOT have been cancelled (all-or-nothing)
        s2 = await schedule_repo.get_by_id(schedules[1].id)
        assert s2 is not None
        assert s2.status == ScheduleStatus.REQUESTED

    async def test_commits_via_uow(
        self,
        service: CancelScheduleGroupService,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group, schedules = _create_group_with_schedules(
            organizer, [UserId.generate()], now
        )
        await schedule_group_repo.save(group)
        for s in schedules:
            await schedule_repo.save(s)

        await service.execute(schedule_group_id=group.id, actor_id=organizer)
        assert uow.committed is True

    async def test_empty_group_succeeds(
        self,
        service: CancelScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
    ) -> None:
        """Cancelling a group with no schedules succeeds with no side effects."""
        organizer = UserId.generate()
        group = ScheduleGroup.create(
            organizer_id=organizer,
            title=ScheduleTitle("Empty"),
            now=datetime.now(UTC),
        )
        group.collect_events()
        await schedule_group_repo.save(group)

        # Should not raise
        await service.execute(schedule_group_id=group.id, actor_id=organizer)
