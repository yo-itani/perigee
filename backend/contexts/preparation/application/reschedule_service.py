"""Use case: Reschedule a Schedule (change datetime directly)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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
class RescheduleInput:
    """Input DTO for RescheduleService."""

    schedule_id: ScheduleId
    actor_id: UserId
    new_scheduled_at: datetime


class RescheduleService:
    """Application service that reschedules a Schedule.

    The datetime change is applied directly via change_scheduled_at().
    Status reverts to REQUESTED (re-confirmation needed).
    Both organizer and counterpart can reschedule.
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
        input_dto: RescheduleInput,
    ) -> None:
        """Reschedule the schedule to a new datetime.

        Args:
            input_dto: Input parameters for rescheduling.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            ScheduleAlreadyCancelledError: If the schedule is cancelled.
            UnauthorizedScheduleOperationError: If actor is not a participant.
        """
        now = datetime.now(UTC)

        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        schedule.change_scheduled_at(
            actor_id=input_dto.actor_id,
            new_scheduled_at=input_dto.new_scheduled_at,
            now=now,
        )

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)
