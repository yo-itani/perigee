"""Tests for RenameScheduleGroupService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.rename_schedule_group_service import (
    RenameScheduleGroupService,
)
from contexts.preparation.domain.events import ScheduleGroupRenamed, ScheduleRenamed
from contexts.preparation.domain.exceptions import (
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.domain.exceptions import EntityNotFoundError
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


async def _setup_group(
    schedule_group_repo: InMemoryScheduleGroupRepository,
    schedule_repo: InMemoryScheduleRepository,
    organizer: UserId,
    counterpart_ids: list[UserId],
    now: datetime,
) -> ScheduleGroup:
    """Helper: create and persist a group with schedules."""
    group = ScheduleGroup.create(
        organizer_id=organizer,
        title=ScheduleTitle("Original Title"),
        now=now,
    )
    for i, cp_id in enumerate(counterpart_ids):
        schedule = Schedule.create(
            organizer_id=organizer,
            counterpart_id=cp_id,
            scheduled_at=now + timedelta(days=1 + i),
            requested_by=organizer,
            title=ScheduleTitle("Original Title"),
            schedule_group_id=group.id,
            now=now,
        )
        group.register_schedule(schedule.id)
        schedule.collect_events()
        await schedule_repo.save(schedule)
    group.collect_events()
    await schedule_group_repo.save(group)
    return group


class TestRenameScheduleGroup:
    """Rename a ScheduleGroup and propagate to child schedules."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> RenameScheduleGroupService:
        return RenameScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_renames_group_and_schedules(
        self,
        service: RenameScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Group and all child schedules are renamed."""
        organizer = UserId.generate()
        cp1, cp2 = UserId.generate(), UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [cp1, cp2], now
        )

        await service.execute(
            schedule_group_id=group.id,
            new_title="New Title",
            actor_id=organizer,
        )

        updated_group = await schedule_group_repo.get_by_id(group.id)
        assert updated_group is not None
        assert updated_group.title.value == "New Title"

        for s_id in group.schedule_ids:
            schedule = await schedule_repo.get_by_id(s_id)
            assert schedule is not None
            assert schedule.title.value == "New Title"

    async def test_dispatches_events(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleGroupRenamed and ScheduleRenamed events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleGroupRenamed, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleRenamed, capture)  # type: ignore[arg-type]

        service = RenameScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        await service.execute(
            schedule_group_id=group.id,
            new_title="New Title",
            actor_id=organizer,
        )

        group_events = [e for e in dispatched if isinstance(e, ScheduleGroupRenamed)]
        schedule_events = [e for e in dispatched if isinstance(e, ScheduleRenamed)]
        assert len(group_events) == 1
        assert len(schedule_events) == 1

    async def test_noop_for_same_title(
        self,
        service: RenameScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """No-op when new title equals current title."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleGroupRenamed, capture)  # type: ignore[arg-type]

        service_with_capture = RenameScheduleGroupService(
            uow=service._uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        await service_with_capture.execute(
            schedule_group_id=group.id,
            new_title="Original Title",
            actor_id=organizer,
        )

        assert len(dispatched) == 0

    async def test_rejects_non_organizer(
        self,
        service: RenameScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedScheduleGroupOperationError for non-organizer."""
        organizer = UserId.generate()
        other = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        with pytest.raises(UnauthorizedScheduleGroupOperationError):
            await service.execute(
                schedule_group_id=group.id,
                new_title="New",
                actor_id=other,
            )

    async def test_raises_not_found(
        self,
        service: RenameScheduleGroupService,
    ) -> None:
        """Raises EntityNotFoundError for nonexistent group."""
        with pytest.raises(EntityNotFoundError):
            await service.execute(
                schedule_group_id=ScheduleGroupId.generate(),
                new_title="New",
                actor_id=UserId.generate(),
            )

    async def test_commits_via_uow(
        self,
        service: RenameScheduleGroupService,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        await service.execute(
            schedule_group_id=group.id,
            new_title="New Title",
            actor_id=organizer,
        )
        assert uow.committed is True
