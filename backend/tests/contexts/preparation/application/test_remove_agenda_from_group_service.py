"""Tests for RemoveAgendaFromGroupService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.remove_agenda_from_group_service import (
    RemoveAgendaFromGroupInput,
    RemoveAgendaFromGroupService,
    ScheduleGroupNotFoundError,
)
from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import AgendaRemovedViaGroup
from contexts.preparation.domain.exceptions import (
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


async def _setup_group_with_agendas(
    schedule_group_repo: InMemoryScheduleGroupRepository,
    schedule_repo: InMemoryScheduleRepository,
    agenda_repo: InMemoryAgendaRepository,
    organizer: UserId,
    counterpart_ids: list[UserId],
    topics: list[str],
    now: datetime,
) -> ScheduleGroup:
    """Helper: create group with schedules and agendas."""
    group = ScheduleGroup.create(
        organizer_id=organizer,
        title=ScheduleTitle("Test Group"),
        agenda_templates=[AgendaTemplate(t) for t in topics],
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

        # Create agendas for each schedule
        for t in topics:
            agenda = Agenda.create(
                schedule_id=schedule.id,
                topic=Topic(t),
                added_by=organizer,
                now=now,
            )
            await agenda_repo.save(agenda)

    group.collect_events()
    await schedule_group_repo.save(group)
    return group


class TestRemoveAgendaFromGroup:
    """Remove an agenda topic from all schedules via ScheduleGroup."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> RemoveAgendaFromGroupService:
        return RemoveAgendaFromGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_removes_agenda_from_all_schedules(
        self,
        service: RemoveAgendaFromGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Removes matching agendas from every schedule in the group."""
        organizer = UserId.generate()
        cp1, cp2 = UserId.generate(), UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [cp1, cp2],
            ["Topic A", "Topic B"],
            now,
        )

        # 2 counterparts * 2 topics = 4 agendas initially
        assert len(agenda_repo.agendas) == 4

        await service.execute(
            RemoveAgendaFromGroupInput(
                schedule_group_id=group.id,
                topic="Topic A",
                actor_id=organizer,
            )
        )

        # Should have 2 remaining (Topic B for each schedule)
        assert len(agenda_repo.agendas) == 2
        for agenda in agenda_repo.agendas.values():
            assert agenda.topic.value == "Topic B"

    async def test_removes_agenda_template_from_group(
        self,
        service: RemoveAgendaFromGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """The group's agenda templates list is updated."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [UserId.generate()],
            ["Topic A", "Topic B"],
            now,
        )

        await service.execute(
            RemoveAgendaFromGroupInput(
                schedule_group_id=group.id,
                topic="Topic A",
                actor_id=organizer,
            )
        )

        updated_group = await schedule_group_repo.get_by_id(group.id)
        assert updated_group is not None
        assert len(updated_group.agenda_templates) == 1
        assert updated_group.agenda_templates[0].topic.value == "Topic B"

    async def test_dispatches_event(
        self,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches AgendaRemovedViaGroup event."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(AgendaRemovedViaGroup, capture)  # type: ignore[arg-type]

        service = RemoveAgendaFromGroupService(
            uow=uow,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [UserId.generate()],
            ["Topic A"],
            now,
        )

        await service.execute(
            RemoveAgendaFromGroupInput(
                schedule_group_id=group.id,
                topic="Topic A",
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        assert isinstance(dispatched[0], AgendaRemovedViaGroup)

    async def test_noop_for_nonexistent_topic(
        self,
        service: RemoveAgendaFromGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """No error when removing a topic that does not exist in templates."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [UserId.generate()],
            ["Topic A"],
            now,
        )

        # Should succeed without error (no-op)
        await service.execute(
            RemoveAgendaFromGroupInput(
                schedule_group_id=group.id,
                topic="Nonexistent",
                actor_id=organizer,
            )
        )

        # Agendas unchanged
        assert len(agenda_repo.agendas) == 1

    async def test_rejects_non_organizer(
        self,
        service: RemoveAgendaFromGroupService,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Raises UnauthorizedScheduleGroupOperationError for non-organizer."""
        organizer = UserId.generate()
        other = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [UserId.generate()],
            ["Topic"],
            now,
        )

        with pytest.raises(UnauthorizedScheduleGroupOperationError):
            await service.execute(
                RemoveAgendaFromGroupInput(
                    schedule_group_id=group.id,
                    topic="Topic",
                    actor_id=other,
                )
            )

    async def test_raises_not_found(
        self,
        service: RemoveAgendaFromGroupService,
    ) -> None:
        """Raises ScheduleGroupNotFoundError for nonexistent group."""
        with pytest.raises(ScheduleGroupNotFoundError):
            await service.execute(
                RemoveAgendaFromGroupInput(
                    schedule_group_id=ScheduleGroupId.generate(),
                    topic="Topic",
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: RemoveAgendaFromGroupService,
        uow: StubUnitOfWork,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        now = datetime.now(UTC)
        group = await _setup_group_with_agendas(
            schedule_group_repo,
            schedule_repo,
            agenda_repo,
            organizer,
            [UserId.generate()],
            ["Topic"],
            now,
        )

        await service.execute(
            RemoveAgendaFromGroupInput(
                schedule_group_id=group.id,
                topic="Topic",
                actor_id=organizer,
            )
        )
        assert uow.committed is True
