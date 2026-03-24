"""Tests for CreateScheduleGroupFromPastService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.create_schedule_group_from_past_service import (
    CreateScheduleGroupFromPastInput,
    CreateScheduleGroupFromPastOutput,
    CreateScheduleGroupFromPastService,
    PastCounterpartSchedule,
    SourceScheduleGroupNotFoundError,
    UnauthorizedCopyError,
)
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import ScheduleCreated, ScheduleGroupCreated
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleStatus
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


class TestCreateScheduleGroupFromPast:
    """ScheduleGroup creation by copying a past group."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateScheduleGroupFromPastService:
        return CreateScheduleGroupFromPastService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    def organizer(self) -> UserId:
        return UserId.generate()

    @pytest.fixture
    async def source_group(
        self,
        organizer: UserId,
        schedule_group_repo: InMemoryScheduleGroupRepository,
    ) -> ScheduleGroup:
        """A past ScheduleGroup with 2 agenda templates."""
        group = ScheduleGroup.create(
            organizer_id=organizer,
            title=ScheduleTitle("Past Weekly"),
            agenda_templates=[
                AgendaTemplate("Progress update"),
                AgendaTemplate("Action items"),
            ],
        )
        group.collect_events()
        await schedule_group_repo.save(group)
        return group

    async def test_creates_group_from_past(
        self,
        service: CreateScheduleGroupFromPastService,
        source_group: ScheduleGroup,
        organizer: UserId,
        schedule_group_repo: InMemoryScheduleGroupRepository,
    ) -> None:
        """Creates a new ScheduleGroup copying agenda structure from source."""
        cp = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            CreateScheduleGroupFromPastInput(
                organizer_id=organizer,
                source_schedule_group_id=source_group.id,
                title="New Weekly",
                counterpart_schedules=[
                    PastCounterpartSchedule(counterpart_id=cp, scheduled_at=future),
                ],
            )
        )

        assert isinstance(output, CreateScheduleGroupFromPastOutput)
        group = await schedule_group_repo.get_by_id(output.schedule_group_id)
        assert group is not None
        assert group.title.value == "New Weekly"
        assert group.template_id is None
        assert len(group.schedule_ids) == 1

    async def test_copies_agenda_templates(
        self,
        service: CreateScheduleGroupFromPastService,
        source_group: ScheduleGroup,
        organizer: UserId,
        agenda_repo: InMemoryAgendaRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Agenda templates from source are expanded to new schedules."""
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            CreateScheduleGroupFromPastInput(
                organizer_id=organizer,
                source_schedule_group_id=source_group.id,
                title="Copied",
                counterpart_schedules=[
                    PastCounterpartSchedule(counterpart_id=cp1, scheduled_at=future),
                    PastCounterpartSchedule(
                        counterpart_id=cp2,
                        scheduled_at=future + timedelta(hours=1),
                    ),
                ],
            )
        )

        # 2 counterparts * 2 topics = 4 agendas
        assert len(agenda_repo.agendas) == 4

        for schedule in schedule_repo.schedules.values():
            schedule_agendas = await agenda_repo.get_by_schedule_id(schedule.id)
            topics = {a.topic.value for a in schedule_agendas}
            assert topics == {"Progress update", "Action items"}

    async def test_raises_not_found_for_missing_source(
        self,
        service: CreateScheduleGroupFromPastService,
        organizer: UserId,
    ) -> None:
        """Raises SourceScheduleGroupNotFoundError when source does not exist."""
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(SourceScheduleGroupNotFoundError):
            await service.execute(
                CreateScheduleGroupFromPastInput(
                    organizer_id=organizer,
                    source_schedule_group_id=ScheduleGroupId.generate(),
                    title="Missing",
                    counterpart_schedules=[
                        PastCounterpartSchedule(
                            counterpart_id=UserId.generate(),
                            scheduled_at=future,
                        ),
                    ],
                )
            )

    async def test_raises_unauthorized_for_non_organizer(
        self,
        service: CreateScheduleGroupFromPastService,
        source_group: ScheduleGroup,
    ) -> None:
        """Raises UnauthorizedCopyError for non-organizer of source."""
        other_user = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(UnauthorizedCopyError):
            await service.execute(
                CreateScheduleGroupFromPastInput(
                    organizer_id=other_user,
                    source_schedule_group_id=source_group.id,
                    title="Unauthorized",
                    counterpart_schedules=[
                        PastCounterpartSchedule(
                            counterpart_id=UserId.generate(),
                            scheduled_at=future,
                        ),
                    ],
                )
            )

    async def test_commits_via_uow(
        self,
        service: CreateScheduleGroupFromPastService,
        source_group: ScheduleGroup,
        organizer: UserId,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            CreateScheduleGroupFromPastInput(
                organizer_id=organizer,
                source_schedule_group_id=source_group.id,
                title="Commit Test",
                counterpart_schedules=[
                    PastCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )
        )
        assert uow.committed is True

    async def test_dispatches_events(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        source_group: ScheduleGroup,
        organizer: UserId,
    ) -> None:
        """Dispatches ScheduleCreated and ScheduleGroupCreated events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCreated, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleGroupCreated, capture)  # type: ignore[arg-type]

        svc = CreateScheduleGroupFromPastService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        future = datetime.now(UTC) + timedelta(days=1)
        await svc.execute(
            CreateScheduleGroupFromPastInput(
                organizer_id=organizer,
                source_schedule_group_id=source_group.id,
                title="Events Test",
                counterpart_schedules=[
                    PastCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                    PastCounterpartSchedule(
                        counterpart_id=UserId.generate(),
                        scheduled_at=future + timedelta(hours=1),
                    ),
                ],
            )
        )

        schedule_created = [e for e in dispatched if isinstance(e, ScheduleCreated)]
        group_created = [e for e in dispatched if isinstance(e, ScheduleGroupCreated)]
        assert len(schedule_created) == 2
        assert len(group_created) == 1

    async def test_schedules_in_requested_status(
        self,
        service: CreateScheduleGroupFromPastService,
        source_group: ScheduleGroup,
        organizer: UserId,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Created schedules start in REQUESTED status."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            CreateScheduleGroupFromPastInput(
                organizer_id=organizer,
                source_schedule_group_id=source_group.id,
                title="Status Test",
                counterpart_schedules=[
                    PastCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )
        )

        for schedule in schedule_repo.schedules.values():
            assert schedule.status == ScheduleStatus.REQUESTED
