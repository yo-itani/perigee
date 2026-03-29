"""Use case: Delete an agenda topic from a Schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.events import AgendaDeleted
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class AgendaNotFoundError(Exception):
    """Raised when the specified Agenda does not exist."""

    def __init__(self, agenda_id: AgendaId) -> None:
        self.agenda_id = agenda_id
        super().__init__(f"Agenda not found: {agenda_id.value}")


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
class DeleteAgendaInput:
    """Input DTO for DeleteAgendaUseCase."""

    schedule_id: ScheduleId
    agenda_id: AgendaId
    actor_id: UserId


class DeleteAgendaUseCase:
    """Application service that deletes an agenda topic from a schedule.

    Both organizer and counterpart can delete agendas.
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

    async def execute(self, input_dto: DeleteAgendaInput) -> None:
        """Delete the agenda topic.

        Args:
            input_dto: Input parameters for deleting an agenda.

        Raises:
            AgendaNotFoundError: If the agenda does not exist.
            ScheduleNotFoundError: If the parent schedule does not exist.
            UnauthorizedAgendaOperationError: If actor is not a participant.
        """
        now = datetime.now(UTC)

        agenda = await self._agenda_repo.get_by_id(input_dto.agenda_id)
        if agenda is None:
            raise AgendaNotFoundError(input_dto.agenda_id)

        # Verify that the agenda belongs to the specified schedule
        if agenda.schedule_id != input_dto.schedule_id:
            raise AgendaNotFoundError(input_dto.agenda_id)

        schedule = await self._schedule_repo.get_by_id(agenda.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(agenda.schedule_id)

        # Permission check: only organizer or counterpart
        if (
            input_dto.actor_id != schedule.organizer_id
            and input_dto.actor_id != schedule.counterpart_id
        ):
            raise UnauthorizedAgendaOperationError()

        events: list[DomainEvent] = [
            AgendaDeleted(
                agenda_id=agenda.id,
                schedule_id=agenda.schedule_id,
                deleted_by=input_dto.actor_id,
                occurred_at=now,
            )
        ]

        async with self._uow:
            await self._agenda_repo.delete_by_ids([agenda.id])

        await self._event_dispatcher.dispatch(events)
