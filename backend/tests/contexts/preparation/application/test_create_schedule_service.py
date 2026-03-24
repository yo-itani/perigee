"""Tests for CreateScheduleService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.create_schedule_service import (
    CreateScheduleInput,
    CreateScheduleOutput,
    CreateScheduleService,
)
from contexts.preparation.domain.events import ScheduleConfirmed, ScheduleCreated
from contexts.preparation.domain.exceptions import InvalidScheduleOperationError
from contexts.preparation.domain.value_objects import ScheduleStatus
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


class TestCreateSchedule:
    """Create a single Schedule (individual 1-on-1)."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateScheduleService:
        return CreateScheduleService(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_confirmed_schedule(
        self,
        service: CreateScheduleService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Schedule is created and auto-confirmed."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            CreateScheduleInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Weekly 1-on-1",
            )
        )

        assert isinstance(output, CreateScheduleOutput)
        schedule = await schedule_repo.get_by_id(output.schedule_id)
        assert schedule is not None
        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.organizer_id == organizer
        assert schedule.counterpart_id == counterpart
        assert schedule.title.value == "Weekly 1-on-1"

    async def test_dispatches_created_and_confirmed_events(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Dispatches ScheduleCreated and ScheduleConfirmed events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCreated, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleConfirmed, capture)  # type: ignore[arg-type]

        service = CreateScheduleService(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            CreateScheduleInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Weekly 1-on-1",
            )
        )

        assert len(dispatched) == 2
        assert isinstance(dispatched[0], ScheduleCreated)
        assert isinstance(dispatched[1], ScheduleConfirmed)
        assert dispatched[1].is_auto is True

    async def test_rejects_same_organizer_and_counterpart(
        self,
        service: CreateScheduleService,
    ) -> None:
        """Raises InvalidScheduleOperationError when organizer == counterpart."""
        user = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(InvalidScheduleOperationError):
            await service.execute(
                CreateScheduleInput(
                    organizer_id=user,
                    counterpart_id=user,
                    scheduled_at=scheduled_at,
                    title="Self 1-on-1",
                )
            )

    async def test_rejects_past_datetime(
        self,
        service: CreateScheduleService,
    ) -> None:
        """Raises InvalidScheduleOperationError for past scheduled_at."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        past_time = datetime.now(UTC) - timedelta(days=1)

        with pytest.raises(InvalidScheduleOperationError):
            await service.execute(
                CreateScheduleInput(
                    organizer_id=organizer,
                    counterpart_id=counterpart,
                    scheduled_at=past_time,
                    title="Past 1-on-1",
                )
            )

    async def test_commits_via_uow(
        self,
        service: CreateScheduleService,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            CreateScheduleInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Weekly 1-on-1",
            )
        )
        assert uow.committed is True
