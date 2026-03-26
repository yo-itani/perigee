"""Tests for CancelScheduleUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.cancel_schedule_use_case import (
    CancelScheduleInput,
    CancelScheduleUseCase,
    ScheduleNotFoundError,
)
from contexts.preparation.domain.events import ScheduleCancelled
from contexts.preparation.domain.exceptions import (
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId, ScheduleStatus
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
        title=ScheduleTitle("Test Schedule"),
        now=now,
    )
    schedule.auto_confirm(now=now)
    schedule.collect_events()  # Drain factory events
    return schedule


class TestCancelSchedule:
    """Cancel a single Schedule."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CancelScheduleUseCase:
        return CancelScheduleUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_cancels(
        self,
        service: CancelScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Organizer can cancel a schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            CancelScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.status == ScheduleStatus.CANCELLED

    async def test_counterpart_cancels(
        self,
        service: CancelScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Counterpart can also cancel a schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        await service.execute(
            CancelScheduleInput(
                schedule_id=schedule.id,
                actor_id=counterpart,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.status == ScheduleStatus.CANCELLED

    async def test_dispatches_cancelled_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleCancelled event."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCancelled, capture)  # type: ignore[arg-type]

        service = CancelScheduleUseCase(
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
            CancelScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        assert isinstance(dispatched[0], ScheduleCancelled)
        assert dispatched[0].cancelled_by == organizer

    async def test_rejects_non_participant(
        self,
        service: CancelScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedScheduleOperationError for non-participant."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedScheduleOperationError):
            await service.execute(
                CancelScheduleInput(
                    schedule_id=schedule.id,
                    actor_id=outsider,
                )
            )

    async def test_rejects_already_cancelled(
        self,
        service: CancelScheduleUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises ScheduleAlreadyCancelledError for already cancelled schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        schedule.cancel(actor_id=organizer, now=now)
        schedule.collect_events()
        await schedule_repo.save(schedule)

        with pytest.raises(ScheduleAlreadyCancelledError):
            await service.execute(
                CancelScheduleInput(
                    schedule_id=schedule.id,
                    actor_id=organizer,
                )
            )

    async def test_raises_not_found(
        self,
        service: CancelScheduleUseCase,
    ) -> None:
        """Raises ScheduleNotFoundError for nonexistent schedule."""
        with pytest.raises(ScheduleNotFoundError):
            await service.execute(
                CancelScheduleInput(
                    schedule_id=ScheduleId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: CancelScheduleUseCase,
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
            CancelScheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )
        assert uow.committed is True
