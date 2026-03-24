"""Tests for DeleteAgendaService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.delete_agenda_service import (
    AgendaNotFoundError,
    DeleteAgendaInput,
    DeleteAgendaService,
    UnauthorizedAgendaOperationError,
)
from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.events import AgendaDeleted
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import AddedByTag, AgendaId
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


def _create_agenda(
    schedule: Schedule,
    organizer: UserId,
    now: datetime,
) -> Agenda:
    """Helper: create an agenda for the given schedule."""
    return Agenda.create(
        schedule_id=schedule.id,
        topic=Topic("Test topic"),
        added_by=organizer,
        added_by_tag=AddedByTag.ORGANIZER,
        now=now,
    )


class TestDeleteAgenda:
    """Delete an agenda topic from a schedule."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> DeleteAgendaService:
        return DeleteAgendaService(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_deletes_agenda(
        self,
        service: DeleteAgendaService,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Organizer can delete an agenda topic."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        await service.execute(
            DeleteAgendaInput(agenda_id=agenda.id, actor_id=organizer)
        )

        assert await agenda_repo.get_by_id(agenda.id) is None

    async def test_counterpart_deletes_agenda(
        self,
        service: DeleteAgendaService,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Counterpart can also delete an agenda topic."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        await service.execute(
            DeleteAgendaInput(agenda_id=agenda.id, actor_id=counterpart)
        )

        assert await agenda_repo.get_by_id(agenda.id) is None

    async def test_dispatches_agenda_deleted_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches AgendaDeleted event after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(AgendaDeleted, capture)  # type: ignore[arg-type]

        service = DeleteAgendaService(
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
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        await service.execute(
            DeleteAgendaInput(agenda_id=agenda.id, actor_id=organizer)
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, AgendaDeleted)
        assert event.agenda_id == agenda.id
        assert event.schedule_id == schedule.id
        assert event.deleted_by == organizer

    async def test_rejects_non_participant(
        self,
        service: DeleteAgendaService,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Raises UnauthorizedAgendaOperationError for non-participant."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        with pytest.raises(UnauthorizedAgendaOperationError):
            await service.execute(
                DeleteAgendaInput(agenda_id=agenda.id, actor_id=outsider)
            )

    async def test_raises_agenda_not_found(
        self,
        service: DeleteAgendaService,
    ) -> None:
        """Raises AgendaNotFoundError for nonexistent agenda."""
        with pytest.raises(AgendaNotFoundError):
            await service.execute(
                DeleteAgendaInput(
                    agenda_id=AgendaId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: DeleteAgendaService,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        await service.execute(
            DeleteAgendaInput(agenda_id=agenda.id, actor_id=organizer)
        )
        assert uow.committed is True
