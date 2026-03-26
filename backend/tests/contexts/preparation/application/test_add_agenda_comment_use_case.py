"""Tests for AddAgendaCommentUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.add_agenda_comment_use_case import (
    AddAgendaCommentInput,
    AddAgendaCommentOutput,
    AddAgendaCommentUseCase,
    AgendaNotFoundError,
    UnauthorizedAgendaCommentError,
)
from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.events import AgendaCommentAdded
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


class TestAddAgendaComment:
    """Add a comment to an agenda topic."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> AddAgendaCommentUseCase:
        return AddAgendaCommentUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_organizer_adds_comment(
        self,
        service: AddAgendaCommentUseCase,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Organizer can add a comment to an agenda."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        output = await service.execute(
            AddAgendaCommentInput(
                agenda_id=agenda.id,
                body="Let's focus on timeline",
                actor_id=organizer,
            )
        )

        assert isinstance(output, AddAgendaCommentOutput)
        updated = await agenda_repo.get_by_id(agenda.id)
        assert updated is not None
        assert len(updated.comments) == 1
        assert updated.comments[0].author_id == organizer
        assert updated.comments[0].body.value == "Let's focus on timeline"

    async def test_counterpart_adds_comment(
        self,
        service: AddAgendaCommentUseCase,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Counterpart can add a comment to an agenda."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        output = await service.execute(
            AddAgendaCommentInput(
                agenda_id=agenda.id,
                body="I have a question",
                actor_id=counterpart,
            )
        )

        updated = await agenda_repo.get_by_id(agenda.id)
        assert updated is not None
        assert len(updated.comments) == 1
        assert updated.comments[0].id == output.comment_id
        assert updated.comments[0].author_id == counterpart

    async def test_dispatches_agenda_comment_added_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Dispatches AgendaCommentAdded event after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(AgendaCommentAdded, capture)  # type: ignore[arg-type]

        service = AddAgendaCommentUseCase(
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

        output = await service.execute(
            AddAgendaCommentInput(
                agenda_id=agenda.id,
                body="Event test comment",
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, AgendaCommentAdded)
        assert event.comment_id == output.comment_id
        assert event.agenda_id == agenda.id
        assert event.schedule_id == schedule.id
        assert event.author_id == organizer

    async def test_rejects_non_participant(
        self,
        service: AddAgendaCommentUseCase,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Raises UnauthorizedAgendaCommentError for non-participant."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        now = datetime.now(UTC)
        schedule = _create_confirmed_schedule(organizer, counterpart, now)
        await schedule_repo.save(schedule)
        agenda = _create_agenda(schedule, organizer, now)
        await agenda_repo.save(agenda)

        with pytest.raises(UnauthorizedAgendaCommentError):
            await service.execute(
                AddAgendaCommentInput(
                    agenda_id=agenda.id,
                    body="Should fail",
                    actor_id=outsider,
                )
            )

    async def test_raises_agenda_not_found(
        self,
        service: AddAgendaCommentUseCase,
    ) -> None:
        """Raises AgendaNotFoundError for nonexistent agenda."""
        with pytest.raises(AgendaNotFoundError):
            await service.execute(
                AddAgendaCommentInput(
                    agenda_id=AgendaId.generate(),
                    body="No agenda",
                    actor_id=UserId.generate(),
                )
            )

    async def test_commits_via_uow(
        self,
        service: AddAgendaCommentUseCase,
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
            AddAgendaCommentInput(
                agenda_id=agenda.id,
                body="Commit test",
                actor_id=organizer,
            )
        )
        assert uow.committed is True
