"""Use case: Create a ScheduleGroup with schedules for multiple counterparts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId, TemplateId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class CounterpartSchedule:
    """Input DTO: per-counterpart scheduling parameters."""

    counterpart_id: UserId
    scheduled_at: datetime


class CreateScheduleGroupService:
    """Application service that creates a ScheduleGroup with individual Schedules.

    The organizer specifies multiple counterparts, each with their own
    scheduled datetime. Template agendas are expanded into Agenda entities
    for every created Schedule.

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
        organizer_id: UserId,
        title: str,
        counterpart_schedules: list[CounterpartSchedule],
        agenda_topics: list[str] | None = None,
        template_id: str | None = None,
    ) -> ScheduleGroupId:
        """Create a schedule group and return its id.

        Args:
            organizer_id: The user creating the group (organizer).
            title: Title for the schedule group and its schedules.
            counterpart_schedules: Per-counterpart scheduling info.
            agenda_topics: Optional agenda topics to expand to all schedules.
            template_id: Optional source template ID.

        Returns:
            The id of the newly created schedule group.
        """
        now = datetime.now(UTC)
        schedule_title = ScheduleTitle(title)
        tid = TemplateId.from_str(template_id) if template_id else None

        templates = [AgendaTemplate(t) for t in (agenda_topics or [])]

        group = ScheduleGroup.create(
            organizer_id=organizer_id,
            title=schedule_title,
            agenda_templates=templates,
            template_id=tid,
            now=now,
        )

        all_events: list[DomainEvent] = []
        all_agendas: list[Agenda] = []
        schedules: list[Schedule] = []

        for cs in counterpart_schedules:
            schedule = Schedule.create(
                organizer_id=organizer_id,
                counterpart_id=cs.counterpart_id,
                scheduled_at=cs.scheduled_at,
                requested_by=organizer_id,
                title=schedule_title,
                schedule_group_id=group.id,
                now=now,
            )
            group.register_schedule(schedule.id)
            schedules.append(schedule)

            # Expand agenda templates into agenda entities
            for tmpl in group.agenda_templates:
                agenda = Agenda.create(
                    schedule_id=schedule.id,
                    topic=tmpl.topic,
                    added_by=organizer_id,
                    now=now,
                )
                all_agendas.append(agenda)

        # Collect events from all entities
        for schedule in schedules:
            all_events.extend(schedule.collect_events())
        all_events.extend(group.collect_events())

        # Single transaction: all-or-nothing
        async with self._uow:
            await self._schedule_group_repo.save(group)
            for schedule in schedules:
                await self._schedule_repo.save(schedule)
            if all_agendas:
                await self._agenda_repo.save_all(all_agendas)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)

        return group.id
