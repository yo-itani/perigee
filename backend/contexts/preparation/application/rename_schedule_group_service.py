"""Use case: Rename a ScheduleGroup and propagate to its schedules."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from foundation.domain.exceptions import EntityNotFoundError
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class RenameScheduleGroupService:
    """Application service that renames a ScheduleGroup and its schedules.

    Delegates to ScheduleGroup.rename for domain logic (authorization,
    no-op detection, consistency check, and propagation to child schedules).
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
        new_title: str,
        actor_id: UserId,
    ) -> None:
        """Rename the schedule group and propagate to all child schedules.

        Args:
            schedule_group_id: The group to rename.
            new_title: The new title string.
            actor_id: The user performing the operation (must be organizer).

        Raises:
            EntityNotFoundError: If the schedule group does not exist.
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
            InconsistentSchedulesError: If loaded schedules do not match
                registered schedule IDs.
        """
        now = datetime.now(UTC)
        title = ScheduleTitle(new_title)

        group = await self._schedule_group_repo.get_by_id(schedule_group_id)
        if group is None:
            raise EntityNotFoundError("ScheduleGroup", str(schedule_group_id.value))

        schedules = await self._schedule_repo.get_by_schedule_group_id(
            schedule_group_id
        )

        group.rename(
            title=title,
            actor_id=actor_id,
            now=now,
            schedules=schedules,
        )

        all_events: list[DomainEvent] = list(group.collect_events())
        for schedule in schedules:
            all_events.extend(schedule.collect_events())

        # Single transaction: all-or-nothing
        async with self._uow:
            await self._schedule_group_repo.save(group)
            for schedule in schedules:
                await self._schedule_repo.save(schedule)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)
