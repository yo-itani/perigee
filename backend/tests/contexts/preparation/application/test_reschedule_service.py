"""Tests for RescheduleService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.reschedule_service import (
    RescheduleInput,
    RescheduleService,
    ScheduleNotFoundError,
)
from contexts.preparation.domain.events import (
    ScheduleConfirmed,
    ScheduleRescheduled,
)
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


class TestReschedule:
    """Reschedule a Schedule (change datetime)."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> RescheduleService:
        return RescheduleService(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_reschedules(
        self,
        service: RescheduleService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Organizer can reschedule and the new datetime is applied."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        new_time = now + timedelta(days=7)
        await service.execute(
            RescheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                new_scheduled_at=new_time,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.status == ScheduleStatus.CONFIRMED
        assert updated.scheduled_at == new_time

    async def test_counterpart_reschedules(
        self,
        service: RescheduleService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Counterpart can also reschedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        new_time = now + timedelta(days=3)
        await service.execute(
            RescheduleInput(
                schedule_id=schedule.id,
                actor_id=counterpart,
                new_scheduled_at=new_time,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.status == ScheduleStatus.CONFIRMED

    async def test_dispatches_rescheduled_and_confirmed_events(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleRescheduled and ScheduleConfirmed events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleRescheduled, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleConfirmed, capture)  # type: ignore[arg-type]

        service = RescheduleService(
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
            RescheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                new_scheduled_at=now + timedelta(days=5),
            )
        )

        assert len(dispatched) == 2
        assert isinstance(dispatched[0], ScheduleRescheduled)
        assert isinstance(dispatched[1], ScheduleConfirmed)
        assert dispatched[1].is_auto is True

    async def test_rejects_non_participant(
        self,
        service: RescheduleService,
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
                RescheduleInput(
                    schedule_id=schedule.id,
                    actor_id=outsider,
                    new_scheduled_at=now + timedelta(days=5),
                )
            )

    async def test_rejects_cancelled_schedule(
        self,
        service: RescheduleService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises ScheduleAlreadyCancelledError for cancelled schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        schedule.cancel(actor_id=organizer, now=now)
        schedule.collect_events()
        await schedule_repo.save(schedule)

        with pytest.raises(ScheduleAlreadyCancelledError):
            await service.execute(
                RescheduleInput(
                    schedule_id=schedule.id,
                    actor_id=organizer,
                    new_scheduled_at=now + timedelta(days=5),
                )
            )

    async def test_raises_not_found(
        self,
        service: RescheduleService,
    ) -> None:
        """Raises ScheduleNotFoundError for nonexistent schedule."""
        with pytest.raises(ScheduleNotFoundError):
            await service.execute(
                RescheduleInput(
                    schedule_id=ScheduleId.generate(),
                    actor_id=UserId.generate(),
                    new_scheduled_at=datetime.now(UTC) + timedelta(days=1),
                )
            )

    async def test_commits_via_uow(
        self,
        service: RescheduleService,
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
            RescheduleInput(
                schedule_id=schedule.id,
                actor_id=organizer,
                new_scheduled_at=now + timedelta(days=5),
            )
        )
        assert uow.committed is True
