"""Read-only query service: list agendas for a schedule.

Returns all agendas (with comments) belonging to a Schedule,
ordered by created_at ascending.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.exceptions import UnauthorizedScheduleOperationError
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import (
    AddedByTag,
    AgendaId,
    CommentId,
    ScheduleId,
)
from shared.domain.value_objects import UserId


class ScheduleNotFoundError(Exception):
    """Raised when the specified Schedule does not exist."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id.value}")


@dataclass(frozen=True)
class AgendaCommentDTO:
    """Single comment within an agenda."""

    comment_id: CommentId
    author_id: UserId
    body: str
    created_at: datetime


@dataclass(frozen=True)
class AgendaItemDTO:
    """Single agenda item with its comments."""

    agenda_id: AgendaId
    topic: str
    added_by: UserId
    added_by_tag: AddedByTag
    comments: list[AgendaCommentDTO]
    created_at: datetime


@dataclass(frozen=True)
class ListScheduleAgendasInput:
    """Input DTO for ListScheduleAgendasService."""

    schedule_id: ScheduleId
    actor_id: UserId


@dataclass(frozen=True)
class ListScheduleAgendasOutput:
    """Output DTO for ListScheduleAgendasService."""

    agendas: list[AgendaItemDTO]


class ListScheduleAgendasService:
    """Query all agendas for a Schedule.

    Authorization: the actor must be the organizer or counterpart.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        agenda_repo: AgendaRepository,
    ) -> None:
        self._schedule_repo = schedule_repo
        self._agenda_repo = agenda_repo

    async def execute(
        self, input_dto: ListScheduleAgendasInput
    ) -> ListScheduleAgendasOutput:
        """List agendas for the schedule.

        Args:
            input_dto: Input containing the schedule ID and actor ID.

        Returns:
            Output containing the list of agendas with comments.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            UnauthorizedScheduleOperationError: If actor is not a participant.
        """
        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        # Permission check: only organizer or counterpart
        if (
            input_dto.actor_id != schedule.organizer_id
            and input_dto.actor_id != schedule.counterpart_id
        ):
            raise UnauthorizedScheduleOperationError(
                "Only the organizer or counterpart can view agendas."
            )

        agendas = await self._agenda_repo.get_by_schedule_id(input_dto.schedule_id)

        agenda_items = [
            AgendaItemDTO(
                agenda_id=a.id,
                topic=a.topic.value,
                added_by=a.added_by,
                added_by_tag=a.added_by_tag,
                comments=[
                    AgendaCommentDTO(
                        comment_id=c.id,
                        author_id=c.author_id,
                        body=c.body.value,
                        created_at=c.created_at,
                    )
                    for c in a.comments
                ],
                created_at=a.created_at,
            )
            for a in agendas
        ]

        return ListScheduleAgendasOutput(agendas=agenda_items)
