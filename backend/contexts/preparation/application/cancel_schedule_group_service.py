"""Use case: Cancel all schedules in a ScheduleGroup."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.preparation.domain.exceptions import (
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from foundation.domain.exceptions import EntityNotFoundError
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class CancelScheduleGroupService:
    """Application service that cancels all schedules in a ScheduleGroup.

    All schedules are cancelled in a single transaction (all-or-nothing).
    Already-cancelled schedules cause the entire operation to fail.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        schedule_group_repo: ScheduleGroupRepository,
        schedule_repo: ScheduleRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._schedule_group_repo = schedule_group_repo
        self._schedule_repo = schedule_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        *,
        schedule_group_id: ScheduleGroupId,
        actor_id: UserId,
    ) -> None:
        """Cancel all schedules in the group.

        Args:
            schedule_group_id: The group to cancel.
            actor_id: The user performing the operation (must be organizer).

        Raises:
            EntityNotFoundError: If the schedule group does not exist.
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
            ScheduleAlreadyCancelledError: If any schedule is already
                cancelled (all-or-nothing).
        """
        now = datetime.now(UTC)

        group = await self._schedule_group_repo.get_by_id(schedule_group_id)
        if group is None:
            raise EntityNotFoundError("ScheduleGroup", str(schedule_group_id.value))

        if actor_id != group.organizer_id:
            raise UnauthorizedScheduleGroupOperationError(
                "Only the organizer can cancel this schedule group."
            )

        schedules = await self._schedule_repo.get_by_schedule_group_id(
            schedule_group_id
        )

        all_events: list[DomainEvent] = []

        # Cancel all schedules; if any raises, the whole operation fails
        for schedule in schedules:
            schedule.cancel(actor_id=actor_id, now=now)

        # Collect events after all cancellations succeed
        for schedule in schedules:
            all_events.extend(schedule.collect_events())

        # Single transaction: all-or-nothing
        async with self._uow:
            for schedule in schedules:
                await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)
