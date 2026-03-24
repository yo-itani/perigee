"""Use case: Create a single Schedule (individual 1-on-1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class CreateScheduleInput:
    """Input DTO for CreateScheduleService."""

    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    title: str


@dataclass(frozen=True)
class CreateScheduleOutput:
    """Output DTO for CreateScheduleService."""

    schedule_id: ScheduleId


class CreateScheduleService:
    """Application service that creates a single Schedule.

    The organizer creates a 1-on-1 with a specific counterpart.
    The schedule is directly auto-confirmed (no approval flow for
    organizer-initiated individual schedules).
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
        input_dto: CreateScheduleInput,
    ) -> CreateScheduleOutput:
        """Create a schedule and return its id.

        The schedule is created in REQUESTED status, then immediately
        auto-confirmed since individual creation by the organizer does
        not require counterpart approval.

        Args:
            input_dto: Input parameters for creating a schedule.

        Returns:
            Output containing the id of the newly created schedule.

        Raises:
            InvalidScheduleOperationError: If organizer == counterpart
                or scheduled_at is in the past.
        """
        now = datetime.now(UTC)
        schedule_title = ScheduleTitle(input_dto.title)

        schedule = Schedule.create(
            organizer_id=input_dto.organizer_id,
            counterpart_id=input_dto.counterpart_id,
            scheduled_at=input_dto.scheduled_at,
            requested_by=input_dto.organizer_id,
            title=schedule_title,
            now=now,
        )
        schedule.auto_confirm(now=now)

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return CreateScheduleOutput(schedule_id=schedule.id)
