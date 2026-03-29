"""Use case: Rename a single Schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
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


class UnauthorizedRenameError(Exception):
    """Raised when a non-organizer attempts to rename a schedule."""

    def __init__(self) -> None:
        super().__init__("Only the organizer can rename a schedule.")


@dataclass(frozen=True)
class RenameScheduleInput:
    """Input DTO for RenameScheduleUseCase."""

    schedule_id: ScheduleId
    new_title: str
    actor_id: UserId


class RenameScheduleUseCase:
    """Application service that renames a single Schedule.

    Only the organizer can rename a schedule.
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
        input_dto: RenameScheduleInput,
    ) -> None:
        """Rename the schedule.

        Args:
            input_dto: Input parameters for renaming a schedule.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            UnauthorizedRenameError: If actor is not the organizer.
        """
        now = datetime.now(UTC)
        new_title = ScheduleTitle(input_dto.new_title)

        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        if input_dto.actor_id != schedule.organizer_id:
            raise UnauthorizedRenameError()

        schedule.rename(new_title=new_title, now=now)

        events: list[DomainEvent] = list(schedule.collect_events())

        async with self._uow:
            await self._schedule_repo.save(schedule)

        await self._event_dispatcher.dispatch(events)
