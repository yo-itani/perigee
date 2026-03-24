"""Use case: Add an agenda topic to all schedules in a ScheduleGroup."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.preparation.domain.agenda_repository import AgendaRepository
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


class AddAgendaToGroupService:
    """Application service that adds an agenda topic to all schedules in a group.

    Delegates to ScheduleGroup.add_agenda_to_schedules for domain logic.
    All operations are committed in a single transaction (all-or-nothing).
    """

    def __init__(
        self,
        uow: UnitOfWork,
        schedule_group_repo: ScheduleGroupRepository,
        schedule_repo: ScheduleRepository,
        agenda_repo: AgendaRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._schedule_group_repo = schedule_group_repo
        self._schedule_repo = schedule_repo
        self._agenda_repo = agenda_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        *,
        schedule_group_id: ScheduleGroupId,
        topic: str,
        actor_id: UserId,
    ) -> None:
        """Add an agenda topic to all schedules in the group.

        Args:
            schedule_group_id: The target group.
            topic: The agenda topic to add.
            actor_id: The user performing the operation (must be organizer).

        Raises:
            EntityNotFoundError: If the schedule group does not exist.
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
        """
        now = datetime.now(UTC)

        group = await self._schedule_group_repo.get_by_id(schedule_group_id)
        if group is None:
            raise EntityNotFoundError("ScheduleGroup", str(schedule_group_id.value))

        # Load existing agendas for all schedules in the group
        schedules_agendas = await self._agenda_repo.get_by_schedule_ids(
            group.schedule_ids
        )

        new_agendas = group.add_agenda_to_schedules(
            topic=topic,
            actor_id=actor_id,
            schedules_agendas=schedules_agendas,
            now=now,
        )

        all_events: list[DomainEvent] = list(group.collect_events())

        # Single transaction: all-or-nothing
        async with self._uow:
            await self._schedule_group_repo.save(group)
            if new_agendas:
                await self._agenda_repo.save_all(new_agendas)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)
