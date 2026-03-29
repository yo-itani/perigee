"""Use case: Add an agenda topic to an individual Schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.events import AgendaAdded
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import AddedByTag, AgendaId, ScheduleId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class ScheduleNotFoundError(Exception):
    """Raised when the specified Schedule does not exist."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id.value}")


class UnauthorizedAgendaOperationError(Exception):
    """Raised when a user without permission attempts an agenda operation."""

    def __init__(
        self, message: str = "Only organizer or counterpart can manage agendas."
    ) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class AddAgendaInput:
    """Input DTO for AddAgendaUseCase."""

    schedule_id: ScheduleId
    topic: str
    actor_id: UserId


@dataclass(frozen=True)
class AddAgendaOutput:
    """Output DTO for AddAgendaUseCase."""

    agenda_id: AgendaId


class AddAgendaUseCase:
    """Application service that adds an agenda topic to an individual schedule.

    Both organizer and counterpart can add agendas.
    The added_by_tag is determined by the actor's role in the schedule.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        schedule_repo: ScheduleRepository,
        agenda_repo: AgendaRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._schedule_repo = schedule_repo
        self._agenda_repo = agenda_repo
        self._event_dispatcher = event_dispatcher

    async def execute(self, input_dto: AddAgendaInput) -> AddAgendaOutput:
        """Add an agenda topic to the schedule.

        Args:
            input_dto: Input parameters for adding an agenda.

        Returns:
            Output containing the newly created agenda ID.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            UnauthorizedAgendaOperationError: If actor is not a participant.
        """
        now = datetime.now(UTC)

        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        # Permission check: only organizer or counterpart
        if (
            input_dto.actor_id != schedule.organizer_id
            and input_dto.actor_id != schedule.counterpart_id
        ):
            raise UnauthorizedAgendaOperationError()

        # Determine added_by_tag based on actor role
        added_by_tag = (
            AddedByTag.ORGANIZER
            if input_dto.actor_id == schedule.organizer_id
            else AddedByTag.COUNTERPART
        )

        topic = Topic(input_dto.topic)
        agenda = Agenda.create(
            schedule_id=input_dto.schedule_id,
            topic=topic,
            added_by=input_dto.actor_id,
            added_by_tag=added_by_tag,
            now=now,
        )

        events: list[DomainEvent] = [
            AgendaAdded(
                agenda_id=agenda.id,
                schedule_id=input_dto.schedule_id,
                added_by=input_dto.actor_id,
                occurred_at=now,
            )
        ]

        async with self._uow:
            await self._agenda_repo.save(agenda)

        await self._event_dispatcher.dispatch(events)

        return AddAgendaOutput(agenda_id=agenda.id)
