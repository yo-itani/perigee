"""Tests for CreateScheduleGroupService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.create_schedule_group_service import (
    CounterpartSchedule,
    CreateScheduleGroupService,
)
from contexts.preparation.domain.events import ScheduleCreated, ScheduleGroupCreated
from contexts.preparation.domain.exceptions import (
    InvalidScheduleOperationError,
    InvalidScheduleTitleError,
)
from contexts.preparation.domain.value_objects import ScheduleStatus
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


class TestCreateScheduleGroup:
    """ScheduleGroup creation with multiple counterparts."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateScheduleGroupService:
        return CreateScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_group_and_schedules(
        self,
        service: CreateScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Creates a ScheduleGroup and individual schedules for each counterpart."""
        organizer = UserId.generate()
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        group_id = await service.execute(
            organizer_id=organizer,
            title="Weekly 1on1",
            counterpart_schedules=[
                CounterpartSchedule(counterpart_id=cp1, scheduled_at=future),
                CounterpartSchedule(
                    counterpart_id=cp2,
                    scheduled_at=future + timedelta(hours=1),
                ),
            ],
        )

        group = await schedule_group_repo.get_by_id(group_id)
        assert group is not None
        assert group.title.value == "Weekly 1on1"
        assert group.organizer_id == organizer
        assert len(group.schedule_ids) == 2

        schedules = schedule_repo.schedules
        assert len(schedules) == 2

    async def test_each_schedule_has_individual_datetime(
        self,
        service: CreateScheduleGroupService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Each counterpart's schedule has its own scheduled_at."""
        organizer = UserId.generate()
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        time1 = datetime.now(UTC) + timedelta(days=1)
        time2 = datetime.now(UTC) + timedelta(days=2)

        await service.execute(
            organizer_id=organizer,
            title="Weekly 1on1",
            counterpart_schedules=[
                CounterpartSchedule(counterpart_id=cp1, scheduled_at=time1),
                CounterpartSchedule(counterpart_id=cp2, scheduled_at=time2),
            ],
        )

        schedules = list(schedule_repo.schedules.values())
        scheduled_times = {s.scheduled_at for s in schedules}
        counterpart_ids = {s.counterpart_id for s in schedules}
        assert counterpart_ids == {cp1, cp2}
        assert len(scheduled_times) == 2

    async def test_expands_agenda_templates_to_all_schedules(
        self,
        service: CreateScheduleGroupService,
        agenda_repo: InMemoryAgendaRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Agenda templates are expanded into Agenda entities for each schedule."""
        organizer = UserId.generate()
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            organizer_id=organizer,
            title="Weekly 1on1",
            counterpart_schedules=[
                CounterpartSchedule(counterpart_id=cp1, scheduled_at=future),
                CounterpartSchedule(
                    counterpart_id=cp2,
                    scheduled_at=future + timedelta(hours=1),
                ),
            ],
            agenda_topics=["Progress update", "Blockers"],
        )

        # 2 counterparts * 2 topics = 4 agendas
        assert len(agenda_repo.agendas) == 4

        # Each schedule should have 2 agendas
        for schedule in schedule_repo.schedules.values():
            schedule_agendas = await agenda_repo.get_by_schedule_id(schedule.id)
            assert len(schedule_agendas) == 2
            topics = {a.topic.value for a in schedule_agendas}
            assert topics == {"Progress update", "Blockers"}

    async def test_commits_via_uow(
        self,
        service: CreateScheduleGroupService,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            organizer_id=UserId.generate(),
            title="Test",
            counterpart_schedules=[
                CounterpartSchedule(
                    counterpart_id=UserId.generate(), scheduled_at=future
                ),
            ],
        )
        assert uow.committed is True

    async def test_dispatches_events(
        self,
        service: CreateScheduleGroupService,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches ScheduleCreated and ScheduleGroupCreated events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCreated, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleGroupCreated, capture)  # type: ignore[arg-type]

        svc = CreateScheduleGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        future = datetime.now(UTC) + timedelta(days=1)
        await svc.execute(
            organizer_id=UserId.generate(),
            title="Test",
            counterpart_schedules=[
                CounterpartSchedule(
                    counterpart_id=UserId.generate(), scheduled_at=future
                ),
                CounterpartSchedule(
                    counterpart_id=UserId.generate(),
                    scheduled_at=future + timedelta(hours=1),
                ),
            ],
        )

        schedule_created_events = [
            e for e in dispatched if isinstance(e, ScheduleCreated)
        ]
        group_created_events = [
            e for e in dispatched if isinstance(e, ScheduleGroupCreated)
        ]
        assert len(schedule_created_events) == 2
        assert len(group_created_events) == 1

    async def test_schedules_in_requested_status(
        self,
        service: CreateScheduleGroupService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Created schedules start in REQUESTED status."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            organizer_id=UserId.generate(),
            title="Test",
            counterpart_schedules=[
                CounterpartSchedule(
                    counterpart_id=UserId.generate(), scheduled_at=future
                ),
            ],
        )

        for schedule in schedule_repo.schedules.values():
            assert schedule.status == ScheduleStatus.REQUESTED

    async def test_stores_template_id(
        self,
        service: CreateScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
    ) -> None:
        """Template ID is stored on the group when provided."""
        import uuid

        future = datetime.now(UTC) + timedelta(days=1)
        template_id_str = str(uuid.uuid4())

        group_id = await service.execute(
            organizer_id=UserId.generate(),
            title="From template",
            counterpart_schedules=[
                CounterpartSchedule(
                    counterpart_id=UserId.generate(), scheduled_at=future
                ),
            ],
            template_id=template_id_str,
        )

        group = await schedule_group_repo.get_by_id(group_id)
        assert group is not None
        assert group.template_id is not None
        assert str(group.template_id.value) == template_id_str

    async def test_empty_counterparts_creates_empty_group(
        self,
        service: CreateScheduleGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Creating a group with no counterparts succeeds with no schedules."""
        group_id = await service.execute(
            organizer_id=UserId.generate(),
            title="Empty group",
            counterpart_schedules=[],
        )

        group = await schedule_group_repo.get_by_id(group_id)
        assert group is not None
        assert len(group.schedule_ids) == 0
        assert len(schedule_repo.schedules) == 0

    async def test_rejects_invalid_title(
        self,
        service: CreateScheduleGroupService,
    ) -> None:
        """Raises InvalidScheduleTitleError for empty title."""
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(InvalidScheduleTitleError):
            await service.execute(
                organizer_id=UserId.generate(),
                title="   ",
                counterpart_schedules=[
                    CounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )

    async def test_rejects_same_organizer_and_counterpart(
        self,
        service: CreateScheduleGroupService,
    ) -> None:
        """Raises InvalidScheduleOperationError when organizer == counterpart."""
        user = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(InvalidScheduleOperationError):
            await service.execute(
                organizer_id=user,
                title="Self 1on1",
                counterpart_schedules=[
                    CounterpartSchedule(counterpart_id=user, scheduled_at=future),
                ],
            )
