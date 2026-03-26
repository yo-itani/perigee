"""Tests for RenameScheduleUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.rename_schedule_use_case import (
    RenameScheduleInput,
    RenameScheduleUseCase,
    ScheduleNotFoundError,
    UnauthorizedRenameError,
)
from contexts.preparation.domain.events import ScheduleRenamed
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


def _create_confirmed_schedule(
    organizer: UserId,
    counterpart: UserId,
    now: datetime,
) -> Schedule:
    """Helper: create and auto-confirm a schedule."""
    schedule = Schedule.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        scheduled_at=now + timedelta(days=1),
        requested_by=organizer,
        title=ScheduleTitle("Original Title"),
        now=now,
    )
    schedule.auto_confirm(now=now)
    schedule.collect_events()  # Drain factory events
    return schedule


class TestRenameSchedule:
    """Rename a single Schedule."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> RenameScheduleUseCase:
        return RenameScheduleUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_renames(
        self,
        service: RenameScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Organizer can rename a schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            RenameScheduleInput(
                schedule_id=schedule.id,
                new_title="New Title",
                actor_id=organizer,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.title.value == "New Title"

    async def test_dispatches_renamed_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleRenamed event."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleRenamed, capture)  # type: ignore[arg-type]

        service = RenameScheduleUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            RenameScheduleInput(
                schedule_id=schedule.id,
                new_title="New Title",
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        assert isinstance(dispatched[0], ScheduleRenamed)
        assert dispatched[0].new_title == "New Title"

    async def test_noop_when_same_title(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """No event is dispatched when title is unchanged."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleRenamed, capture)  # type: ignore[arg-type]

        service = RenameScheduleUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            RenameScheduleInput(
                schedule_id=schedule.id,
                new_title="Original Title",
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 0

    async def test_rejects_counterpart(
        self,
        service: RenameScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedRenameError when counterpart tries to rename."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedRenameError):
            await service.execute(
                RenameScheduleInput(
                    schedule_id=schedule.id,
                    new_title="New Title",
                    actor_id=counterpart,
                )
            )

    async def test_rejects_non_participant(
        self,
        service: RenameScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedRenameError when outsider tries to rename."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedRenameError):
            await service.execute(
                RenameScheduleInput(
                    schedule_id=schedule.id,
                    new_title="New Title",
                    actor_id=outsider,
                )
            )

    async def test_raises_not_found(
        self,
        service: RenameScheduleUseCase,
    ) -> None:
        """Raises ScheduleNotFoundError for nonexistent schedule."""
        with pytest.raises(ScheduleNotFoundError):
            await service.execute(
                RenameScheduleInput(
                    schedule_id=ScheduleId.generate(),
                    new_title="New Title",
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: RenameScheduleUseCase,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            RenameScheduleInput(
                schedule_id=schedule.id,
                new_title="New Title",
                actor_id=organizer,
            )
        )
        assert uow.committed is True
