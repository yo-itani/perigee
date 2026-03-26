"""Tests for ListUpcomingSchedulesQueryService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.list_upcoming_schedules_query_service import (
    ListUpcomingSchedulesInput,
    ListUpcomingSchedulesOutput,
    ListUpcomingSchedulesQueryService,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleStatus
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import InMemoryScheduleRepository


def _create_schedule(
    *,
    organizer_id: UserId,
    counterpart_id: UserId,
    scheduled_at: datetime,
    title: str = "1-on-1",
) -> Schedule:
    """Helper to create a Schedule via the domain factory."""
    return Schedule.create(
        organizer_id=organizer_id,
        counterpart_id=counterpart_id,
        scheduled_at=scheduled_at,
        requested_by=organizer_id,
        title=ScheduleTitle(title),
        now=datetime.now(UTC),
    )


class TestListUpcomingSchedules:
    """List upcoming schedules for a participant."""

    @pytest.fixture
    def actor(self) -> UserId:
        return UserId.generate()

    @pytest.fixture
    def other_user(self) -> UserId:
        return UserId.generate()

    @pytest.fixture
    def third_user(self) -> UserId:
        return UserId.generate()

    @pytest.fixture
    def service(
        self,
        schedule_repo: InMemoryScheduleRepository,
    ) -> ListUpcomingSchedulesQueryService:
        return ListUpcomingSchedulesQueryService(schedule_repo=schedule_repo)

    async def test_returns_future_schedules_as_organizer(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Actor's schedules as organizer are included."""
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future,
        )
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert isinstance(output, ListUpcomingSchedulesOutput)
        assert len(output.schedules) == 1
        assert output.schedules[0].schedule_id == schedule.id
        assert output.schedules[0].organizer_id == actor
        assert output.schedules[0].counterpart_id == other_user

    async def test_returns_future_schedules_as_counterpart(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Actor's schedules as counterpart are included."""
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=other_user,
            counterpart_id=actor,
            scheduled_at=future,
        )
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 1
        assert output.schedules[0].schedule_id == schedule.id

    async def test_excludes_cancelled_schedules(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Cancelled schedules are excluded from results."""
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future,
        )
        schedule.cancel(actor_id=actor, now=datetime.now(UTC))
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 0

    async def test_excludes_past_schedules(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Past schedules (scheduled_at < now) are excluded."""
        past = datetime.now(UTC) - timedelta(days=1)
        # Create with a future date, then manipulate scheduled_at to past
        # to simulate a schedule whose time has passed.
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future,
        )
        # Directly set _scheduled_at to past for testing purposes
        schedule._scheduled_at = past  # noqa: SLF001
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 0

    async def test_excludes_unrelated_schedules(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
        third_user: UserId,
    ) -> None:
        """Unrelated schedules are excluded."""
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=other_user,
            counterpart_id=third_user,
            scheduled_at=future,
        )
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 0

    async def test_sorted_by_scheduled_at_ascending(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Results are sorted by scheduled_at ascending (nearest first)."""
        now = datetime.now(UTC)
        far_future = now + timedelta(days=10)
        near_future = now + timedelta(days=1)
        mid_future = now + timedelta(days=5)

        s1 = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=far_future,
            title="Far",
        )
        s2 = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=near_future,
            title="Near",
        )
        s3 = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=mid_future,
            title="Mid",
        )
        await schedule_repo.save(s1)
        await schedule_repo.save(s2)
        await schedule_repo.save(s3)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 3
        assert output.schedules[0].title == "Near"
        assert output.schedules[1].title == "Mid"
        assert output.schedules[2].title == "Far"

    async def test_respects_limit(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Only up to limit schedules are returned."""
        now = datetime.now(UTC)
        for i in range(5):
            s = _create_schedule(
                organizer_id=actor,
                counterpart_id=other_user,
                scheduled_at=now + timedelta(days=i + 1),
                title=f"Schedule {i}",
            )
            await schedule_repo.save(s)

        output = await service.execute(
            ListUpcomingSchedulesInput(actor_id=actor, limit=3)
        )

        assert len(output.schedules) == 3

    async def test_includes_requested_and_confirmed(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Both REQUESTED and CONFIRMED schedules are included."""
        future = datetime.now(UTC) + timedelta(days=1)
        future2 = datetime.now(UTC) + timedelta(days=2)

        requested = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future,
            title="Requested",
        )
        confirmed = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future2,
            title="Confirmed",
        )
        confirmed.confirm(actor_id=other_user, now=datetime.now(UTC))

        await schedule_repo.save(requested)
        await schedule_repo.save(confirmed)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 2
        statuses = {s.status for s in output.schedules}
        assert statuses == {ScheduleStatus.REQUESTED, ScheduleStatus.CONFIRMED}

    async def test_output_contains_all_required_fields(
        self,
        service: ListUpcomingSchedulesQueryService,
        schedule_repo: InMemoryScheduleRepository,
        actor: UserId,
        other_user: UserId,
    ) -> None:
        """Each item contains all required fields."""
        future = datetime.now(UTC) + timedelta(days=1)
        schedule = _create_schedule(
            organizer_id=actor,
            counterpart_id=other_user,
            scheduled_at=future,
            title="Check fields",
        )
        await schedule_repo.save(schedule)

        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 1
        item = output.schedules[0]
        assert item.schedule_id == schedule.id
        assert item.organizer_id == actor
        assert item.counterpart_id == other_user
        assert item.scheduled_at == schedule.scheduled_at
        assert item.status == ScheduleStatus.REQUESTED
        assert item.title == "Check fields"
        assert item.schedule_group_id is None

    async def test_empty_result_when_no_schedules(
        self,
        service: ListUpcomingSchedulesQueryService,
        actor: UserId,
    ) -> None:
        """Returns empty list when no matching schedules exist."""
        output = await service.execute(ListUpcomingSchedulesInput(actor_id=actor))

        assert len(output.schedules) == 0
