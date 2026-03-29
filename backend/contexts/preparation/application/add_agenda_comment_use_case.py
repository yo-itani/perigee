"""Use case: Add a comment to an agenda topic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.comment_body import CommentBody
from contexts.preparation.domain.events import AgendaCommentAdded
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import AgendaId, CommentId, ScheduleId
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


class UnauthorizedAgendaCommentError(Exception):
    """Raised when a user without permission attempts to comment on an agenda."""

    def __init__(
        self,
        message: str = "Only organizer or counterpart can comment on agendas.",
    ) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class AddAgendaCommentInput:
    """Input DTO for AddAgendaCommentUseCase."""

    agenda_id: AgendaId
    body: str
    actor_id: UserId


@dataclass(frozen=True)
class AddAgendaCommentOutput:
    """Output DTO for AddAgendaCommentUseCase."""

    comment_id: CommentId


class AddAgendaCommentUseCase:
    """Application service that adds a comment to an agenda topic.

    Both organizer and counterpart can comment on any agenda.
    Comments are always public (no private comments).
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

    async def execute(self, input_dto: AddAgendaCommentInput) -> AddAgendaCommentOutput:
        """Add a comment to the agenda topic.

        Args:
            input_dto: Input parameters for adding a comment.

        Returns:
            Output containing the newly created comment ID.

        Raises:
            AgendaNotFoundError: If the agenda does not exist.
            ScheduleNotFoundError: If the parent schedule does not exist.
            UnauthorizedAgendaCommentError: If actor is not a participant.
        """
        now = datetime.now(UTC)

        agenda = await self._agenda_repo.get_by_id(input_dto.agenda_id)
        if agenda is None:
            raise AgendaNotFoundError(input_dto.agenda_id)

        schedule = await self._schedule_repo.get_by_id(agenda.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(agenda.schedule_id)

        # Permission check: only organizer or counterpart
        if (
            input_dto.actor_id != schedule.organizer_id
            and input_dto.actor_id != schedule.counterpart_id
        ):
            raise UnauthorizedAgendaCommentError()

        body = CommentBody(input_dto.body)
        comment = agenda.add_comment(
            author_id=input_dto.actor_id,
            body=body,
            now=now,
        )

        events: list[DomainEvent] = [
            AgendaCommentAdded(
                comment_id=comment.id,
                agenda_id=agenda.id,
                schedule_id=agenda.schedule_id,
                author_id=input_dto.actor_id,
                occurred_at=now,
            )
        ]

        async with self._uow:
            await self._agenda_repo.save(agenda)

        await self._event_dispatcher.dispatch(events)

        return AddAgendaCommentOutput(comment_id=comment.id)
