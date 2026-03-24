"""Tests for AddAgendaToGroupService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.add_agenda_to_group_service import (
    AddAgendaToGroupService,
)
from contexts.preparation.domain.events import AgendaAddedViaGroup
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
    InMemoryAgendaRepository,
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
        title=ScheduleTitle("Test Group"),
        now=now,
    )
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
        schedule.collect_events()
        await schedule_repo.save(schedule)
    group.collect_events()
    await schedule_group_repo.save(group)
    return group


class TestAddAgendaToGroup:
    """Add an agenda topic to all schedules via ScheduleGroup."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> AddAgendaToGroupService:
        return AddAgendaToGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_adds_agenda_to_all_schedules(
        self,
        service: AddAgendaToGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Adds an agenda to every schedule in the group."""
        organizer = UserId.generate()
        cp1, cp2 = UserId.generate(), UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [cp1, cp2], now
        )

        await service.execute(
            schedule_group_id=group.id,
            topic="New topic",
            actor_id=organizer,
        )

        assert len(agenda_repo.agendas) == 2
        for agenda in agenda_repo.agendas.values():
            assert agenda.topic.value == "New topic"
            assert agenda.added_by == organizer

    async def test_creates_agenda_template_on_group(
        self,
        service: AddAgendaToGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """The group's agenda templates list is updated."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        await service.execute(
            schedule_group_id=group.id,
            topic="New topic",
            actor_id=organizer,
        )

        updated_group = await schedule_group_repo.get_by_id(group.id)
        assert updated_group is not None
        assert len(updated_group.agenda_templates) == 1
        assert updated_group.agenda_templates[0].topic.value == "New topic"

    async def test_dispatches_event(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches AgendaAddedViaGroup event."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(AgendaAddedViaGroup, capture)  # type: ignore[arg-type]

        service = AddAgendaToGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group(
            schedule_group_repo, schedule_repo, organizer, [UserId.generate()], now
        )

        await service.execute(
            schedule_group_id=group.id,
            topic="Topic",
            actor_id=organizer,
        )

        assert len(dispatched) == 1
        assert isinstance(dispatched[0], AgendaAddedViaGroup)

    async def test_rejects_non_organizer(
        self,
        service: AddAgendaToGroupService,
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
                topic="Topic",
                actor_id=other,
            )

    async def test_raises_not_found(
        self,
        service: AddAgendaToGroupService,
    ) -> None:
        """Raises EntityNotFoundError for nonexistent group."""
        with pytest.raises(EntityNotFoundError):
            await service.execute(
                schedule_group_id=ScheduleGroupId.generate(),
                topic="Topic",
                actor_id=UserId.generate(),
            )

    async def test_commits_via_uow(
        self,
        service: AddAgendaToGroupService,
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
            topic="Topic",
            actor_id=organizer,
        )
        assert uow.committed is True
