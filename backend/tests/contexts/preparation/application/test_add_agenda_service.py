"""Tests for AddAgendaService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.add_agenda_service import (
    AddAgendaInput,
    AddAgendaService,
    ScheduleNotFoundError,
    UnauthorizedAgendaOperationError,
)
from contexts.preparation.domain.events import AgendaAdded
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import AddedByTag, ScheduleId
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
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


class TestAddAgenda:
    """Add an agenda topic to a schedule."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> AddAgendaService:
        return AddAgendaService(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_adds_agenda(
        self,
        service: AddAgendaService,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Organizer can add an agenda topic."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        output = await service.execute(
            AddAgendaInput(
                schedule_id=schedule.id,
                topic="Discuss project status",
                actor_id=organizer,
            )
        )

        agenda = await agenda_repo.get_by_id(output.agenda_id)
        assert agenda is not None
        assert agenda.topic.value == "Discuss project status"
        assert agenda.added_by == organizer
        assert agenda.added_by_tag == AddedByTag.ORGANIZER

    async def test_counterpart_adds_agenda(
        self,
        service: AddAgendaService,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Counterpart can add an agenda topic."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        output = await service.execute(
            AddAgendaInput(
                schedule_id=schedule.id,
                topic="My topic",
                actor_id=counterpart,
            )
        )

        agenda = await agenda_repo.get_by_id(output.agenda_id)
        assert agenda is not None
        assert agenda.added_by == counterpart
        assert agenda.added_by_tag == AddedByTag.COUNTERPART

    async def test_dispatches_agenda_added_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches AgendaAdded event after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(AgendaAdded, capture)  # type: ignore[arg-type]

        service = AddAgendaService(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        output = await service.execute(
            AddAgendaInput(
                schedule_id=schedule.id,
                topic="Event test",
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, AgendaAdded)
        assert event.agenda_id == output.agenda_id
        assert event.schedule_id == schedule.id
        assert event.added_by == organizer

    async def test_rejects_non_participant(
        self,
        service: AddAgendaService,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises UnauthorizedAgendaOperationError for non-participant."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedAgendaOperationError):
            await service.execute(
                AddAgendaInput(
                    schedule_id=schedule.id,
                    topic="Should fail",
                    actor_id=outsider,
                )
            )

    async def test_raises_schedule_not_found(
        self,
        service: AddAgendaService,
    ) -> None:
        """Raises ScheduleNotFoundError for nonexistent schedule."""
        with pytest.raises(ScheduleNotFoundError):
            await service.execute(
                AddAgendaInput(
                    schedule_id=ScheduleId.generate(),
                    topic="No schedule",
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: AddAgendaService,
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
            AddAgendaInput(
                schedule_id=schedule.id,
                topic="Commit test",
                actor_id=organizer,
            )
        )
        assert uow.committed is True
