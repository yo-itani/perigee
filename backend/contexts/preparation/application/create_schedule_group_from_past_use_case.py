"""Use case: Create a ScheduleGroup by copying from a past ScheduleGroup."""

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
from contexts.preparation.domain.value_objects import AddedByTag, ScheduleGroupId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class PastCounterpartSchedule:
    """Per-counterpart scheduling parameters when copying from past."""

    counterpart_id: UserId
    scheduled_at: datetime


@dataclass(frozen=True)
class CreateScheduleGroupFromPastInput:
    """Input DTO for CreateScheduleGroupFromPastUseCase.

    The organizer references a past ScheduleGroup whose agenda structure
    will be copied into a new ScheduleGroup.
    """

    organizer_id: UserId
    source_schedule_group_id: ScheduleGroupId
    title: str
    counterpart_schedules: list[PastCounterpartSchedule]


@dataclass(frozen=True)
class CreateScheduleGroupFromPastOutput:
    """Output DTO for CreateScheduleGroupFromPastUseCase."""

    schedule_group_id: ScheduleGroupId


class SourceScheduleGroupNotFoundError(Exception):
    """Raised when the source schedule group does not exist."""

    def __init__(self, message: str = "Source schedule group not found.") -> None:
        super().__init__(message)


class UnauthorizedCopyError(Exception):
    """Raised when the actor is not the organizer of the source group."""

    def __init__(
        self,
        message: str = "Only the organizer of the source group can copy it.",
    ) -> None:
        super().__init__(message)


class CreateScheduleGroupFromPastUseCase:
    """Application service that creates a ScheduleGroup by copying a past one.

    The source group's agenda templates are copied into the new group.
    The organizer provides new counterparts and schedules.
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
        input_dto: CreateScheduleGroupFromPastInput,
    ) -> CreateScheduleGroupFromPastOutput:
        """Create a schedule group by copying from a past group.

        Args:
            input_dto: Input parameters for copying a schedule group.

        Returns:
            Output containing the id of the newly created schedule group.

        Raises:
            SourceScheduleGroupNotFoundError: If the source group does
                not exist.
            UnauthorizedCopyError: If the actor is not the organizer of
                the source group.
        """
        now = datetime.now(UTC)

        source = await self._schedule_group_repo.get_by_id(
            input_dto.source_schedule_group_id
        )
        if source is None:
            raise SourceScheduleGroupNotFoundError()

        if source.organizer_id != input_dto.organizer_id:
            raise UnauthorizedCopyError()

        schedule_title = ScheduleTitle(input_dto.title)

        group = ScheduleGroup.create(
            organizer_id=input_dto.organizer_id,
            title=schedule_title,
            agenda_templates=list(source.agenda_templates),
            template_id=None,
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

        return CreateScheduleGroupFromPastOutput(
            schedule_group_id=group.id,
        )
