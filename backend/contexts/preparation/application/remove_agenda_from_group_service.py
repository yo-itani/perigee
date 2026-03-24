"""Use case: Remove an agenda topic from all schedules in a ScheduleGroup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class ScheduleGroupNotFoundError(Exception):
    """Raised when the specified ScheduleGroup does not exist."""

    def __init__(self, schedule_group_id: ScheduleGroupId) -> None:
        self.schedule_group_id = schedule_group_id
        super().__init__(f"ScheduleGroup not found: {schedule_group_id.value}")


@dataclass(frozen=True)
class RemoveAgendaFromGroupInput:
    """Input DTO for RemoveAgendaFromGroupService."""

    schedule_group_id: ScheduleGroupId
    topic: str
    actor_id: UserId


class RemoveAgendaFromGroupService:
    """Application service that removes an agenda topic from all schedules.

    Delegates to ScheduleGroup.remove_agenda_from_schedules for domain logic.
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
        input_dto: RemoveAgendaFromGroupInput,
    ) -> None:
        """Remove an agenda topic from all schedules in the group.

        Args:
            input_dto: Input parameters for removing an agenda from a group.

        Raises:
            ScheduleGroupNotFoundError: If the schedule group does not exist.
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
        """
        now = datetime.now(UTC)

        group = await self._schedule_group_repo.get_by_id(input_dto.schedule_group_id)
        if group is None:
            raise ScheduleGroupNotFoundError(input_dto.schedule_group_id)

        # Load existing agendas for all schedules in the group
        schedules_agendas = await self._agenda_repo.get_by_schedule_ids(
            group.schedule_ids
        )

        removed_ids = group.remove_agenda_from_schedules(
            topic=input_dto.topic,
            actor_id=input_dto.actor_id,
            schedules_agendas=schedules_agendas,
            now=now,
        )

        all_events: list[DomainEvent] = list(group.collect_events())

        # Single transaction: all-or-nothing
        async with self._uow:
            await self._schedule_group_repo.save(group)
            if removed_ids:
                await self._agenda_repo.delete_by_ids(removed_ids)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)
