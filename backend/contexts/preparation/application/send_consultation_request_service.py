"""Use case: Send a consultation request (ad-hoc pattern B).

The counterpart sends a consultation request to the organizer.
A Schedule is created in REQUESTED status with a CREATION-type
ConfirmationRequest. The counterpart provides agendas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.exceptions import UnauthorizedScheduleOperationError
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import ScheduleId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class SendConsultationRequestInput:
    """Input DTO for SendConsultationRequestService."""

    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    title: str
    agenda_topics: list[str]
    actor_id: UserId


@dataclass(frozen=True)
class SendConsultationRequestOutput:
    """Output DTO for SendConsultationRequestService."""

    schedule_id: ScheduleId


class SendConsultationRequestService:
    """Application service for ad-hoc consultation requests.

    The counterpart initiates a consultation request to the organizer.
    The organizer cannot send a consultation request (only the counterpart can).
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

    async def execute(
        self,
        input_dto: SendConsultationRequestInput,
    ) -> SendConsultationRequestOutput:
        """Send a consultation request.

        Only the counterpart can send a consultation request.
        The organizer cannot initiate this flow.

        Args:
            input_dto: Input parameters for the consultation request.

        Returns:
            Output containing the id of the newly created schedule.

        Raises:
            UnauthorizedScheduleOperationError: If the actor is not the
                counterpart (e.g. organizer attempts to send).
            InvalidScheduleOperationError: If organizer == counterpart
                or scheduled_at is in the past.
        """
        if input_dto.actor_id != input_dto.counterpart_id:
            raise UnauthorizedScheduleOperationError(
                "Only the counterpart can send a consultation request."
            )

        now = datetime.now(UTC)
        schedule_title = ScheduleTitle(input_dto.title)

        # The counterpart is the requester in ad-hoc consultation
        schedule = Schedule.create(
            organizer_id=input_dto.organizer_id,
            counterpart_id=input_dto.counterpart_id,
            scheduled_at=input_dto.scheduled_at,
            requested_by=input_dto.counterpart_id,
            title=schedule_title,
            now=now,
        )

        # Create agendas from the counterpart's topics
        agendas: list[Agenda] = []
        for topic_str in input_dto.agenda_topics:
            agenda = Agenda.create(
                schedule_id=schedule.id,
                topic=Topic(topic_str),
                added_by=input_dto.counterpart_id,
                now=now,
            )
            agendas.append(agenda)

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)
            if agendas:
                await self._agenda_repo.save_all(agendas)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return SendConsultationRequestOutput(schedule_id=schedule.id)
