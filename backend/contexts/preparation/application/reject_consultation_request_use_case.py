"""Use case: Reject a consultation request (ad-hoc pattern B).

The organizer rejects the consultation request.
Since this is a CREATION-type ConfirmationRequest, rejecting it
cancels the schedule entirely (ScheduleCancelled event).
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
class RejectConsultationRequestInput:
    """Input DTO for RejectConsultationRequestUseCase."""

    schedule_id: ScheduleId
    actor_id: UserId


class RejectConsultationRequestUseCase:
    """Application service that rejects a consultation request.

    Only the organizer can reject a consultation request sent by
    the counterpart. Rejecting a CREATION-type request cancels
    the schedule entirely.
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
        input_dto: RejectConsultationRequestInput,
    ) -> None:
        """Reject the consultation request.

        The organizer rejects the schedule. The domain's reject()
        method handles the pending ConfirmationRequest rejection.
        For CREATION-type requests, this results in schedule cancellation.

        Args:
            input_dto: Input parameters for rejecting.

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

        # Only the organizer can reject a consultation request
        if input_dto.actor_id != schedule.organizer_id:
            raise UnauthorizedScheduleOperationError(
                "Only the organizer can reject a consultation request."
            )

        schedule.reject(actor_id=input_dto.actor_id, now=now)

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)
