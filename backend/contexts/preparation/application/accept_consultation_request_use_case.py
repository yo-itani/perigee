"""Use case: Accept a consultation request (ad-hoc pattern B).

The organizer accepts the consultation request, confirming the schedule.
The Schedule transitions from REQUESTED to CONFIRMED.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.exceptions import UnauthorizedScheduleOperationError
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class ScheduleNotFoundError(Exception):
    """Raised when the specified Schedule does not exist."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id.value}")


@dataclass(frozen=True)
class AcceptConsultationRequestInput:
    """Input DTO for AcceptConsultationRequestUseCase."""

    schedule_id: ScheduleId
    actor_id: UserId


class AcceptConsultationRequestUseCase:
    """Application service that accepts a consultation request.

    Only the organizer can accept (confirm) a consultation request
    sent by the counterpart.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        schedule_repo: ScheduleRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._schedule_repo = schedule_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        input_dto: AcceptConsultationRequestInput,
    ) -> None:
        """Accept the consultation request.

        The organizer confirms the schedule. The domain's confirm()
        method handles the pending ConfirmationRequest approval and
        status transition.

        Args:
            input_dto: Input parameters for accepting.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            UnauthorizedScheduleOperationError: If the actor is not
                the organizer.
            ScheduleAlreadyCancelledError: If the schedule is cancelled.
            NoPendingConfirmationRequestError: If no pending request.
        """
        now = datetime.now(UTC)

        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        # Only the organizer can accept a consultation request
        if input_dto.actor_id != schedule.organizer_id:
            raise UnauthorizedScheduleOperationError(
                "Only the organizer can accept a consultation request."
            )

        schedule.confirm(actor_id=input_dto.actor_id, now=now)

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)
