"""Use case: Create a ScheduleGroup from a saved template."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import (
    AddedByTag,
    ScheduleGroupId,
    TemplateId,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class TemplateCounterpartSchedule:
    """Per-counterpart scheduling parameters when creating from a template."""

    counterpart_id: UserId
    scheduled_at: datetime


@dataclass(frozen=True)
class CreateScheduleGroupFromTemplateInput:
    """Input DTO for CreateScheduleGroupFromTemplateUseCase.

    The organizer can override counterparts from the template defaults,
    but must provide scheduled_at for each counterpart.
    """

    organizer_id: UserId
    template_id: TemplateId
    title: str
    counterpart_schedules: list[TemplateCounterpartSchedule]


@dataclass(frozen=True)
class CreateScheduleGroupFromTemplateOutput:
    """Output DTO for CreateScheduleGroupFromTemplateUseCase."""

    schedule_group_id: ScheduleGroupId


class TemplateNotFoundError(Exception):
    """Raised when the referenced template does not exist."""

    def __init__(self, message: str = "Template not found.") -> None:
        super().__init__(message)


class UnauthorizedTemplateUseError(Exception):
    """Raised when the actor is not the template owner."""

    def __init__(
        self,
        message: str = "Only the template owner can create a group from this template.",
    ) -> None:
        super().__init__(message)


class CreateScheduleGroupFromTemplateUseCase:
    """Application service that creates a ScheduleGroup from a saved template.

    The template's agenda topics are expanded into Agenda entities for
    each Schedule. The organizer provides counterpart schedules (which
    may differ from template defaults).
    """

    def __init__(
        self,
        uow: UnitOfWork,
        template_repo: TemplateRepository,
        schedule_group_repo: ScheduleGroupRepository,
        schedule_repo: ScheduleRepository,
        agenda_repo: AgendaRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._template_repo = template_repo
        self._schedule_group_repo = schedule_group_repo
        self._schedule_repo = schedule_repo
        self._agenda_repo = agenda_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        input_dto: CreateScheduleGroupFromTemplateInput,
    ) -> CreateScheduleGroupFromTemplateOutput:
        """Create a schedule group from a template.

        Args:
            input_dto: Input parameters for creating a schedule group
                from a template.

        Returns:
            Output containing the id of the newly created schedule group.

        Raises:
            TemplateNotFoundError: If the template does not exist.
            UnauthorizedTemplateUseError: If the actor is not the
                template owner.
        """
        now = datetime.now(UTC)

        template = await self._template_repo.get_by_id(input_dto.template_id)
        if template is None:
            raise TemplateNotFoundError()

        if template.organizer_id != input_dto.organizer_id:
            raise UnauthorizedTemplateUseError()

        schedule_title = ScheduleTitle(input_dto.title)

        group = ScheduleGroup.create(
            organizer_id=input_dto.organizer_id,
            title=schedule_title,
            agenda_templates=list(template.agenda_templates),
            template_id=template.id,
            now=now,
        )

        all_events: list[DomainEvent] = []
        all_agendas: list[Agenda] = []
        schedules: list[Schedule] = []

        for cs in input_dto.counterpart_schedules:
            schedule = Schedule.create(
                organizer_id=input_dto.organizer_id,
                counterpart_id=cs.counterpart_id,
                scheduled_at=cs.scheduled_at,
                requested_by=input_dto.organizer_id,
                title=schedule_title,
                schedule_group_id=group.id,
                now=now,
            )
            group.register_schedule(schedule.id)
            schedules.append(schedule)

            for tmpl in group.agenda_templates:
                agenda = Agenda.create(
                    schedule_id=schedule.id,
                    topic=tmpl.topic,
                    added_by=input_dto.organizer_id,
                    added_by_tag=AddedByTag.TEMPLATE,
                    now=now,
                )
                all_agendas.append(agenda)

        for schedule in schedules:
            all_events.extend(schedule.collect_events())
        all_events.extend(group.collect_events())

        async with self._uow:
            await self._schedule_group_repo.save(group)
            for schedule in schedules:
                await self._schedule_repo.save(schedule)
            if all_agendas:
                await self._agenda_repo.save_all(all_agendas)
            await self._uow.commit()

        await self._event_dispatcher.dispatch(all_events)

        return CreateScheduleGroupFromTemplateOutput(
            schedule_group_id=group.id,
        )
