"""Use case: Save a ScheduleGroup's settings as a reusable template."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import TemplateId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class SaveTemplateInput:
    """Input DTO for SaveTemplateUseCase."""

    organizer_id: UserId
    name: str
    default_counterpart_ids: list[UserId]
    agenda_topics: list[str]


@dataclass(frozen=True)
class SaveTemplateOutput:
    """Output DTO for SaveTemplateUseCase."""

    template_id: TemplateId


class SaveTemplateUseCase:
    """Application service that saves a template for reuse.

    The organizer provides a name, default counterparts, and agenda topics.
    A new Template aggregate is created and persisted, then a TemplateSaved
    domain event is dispatched after commit.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        template_repo: TemplateRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._template_repo = template_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        input_dto: SaveTemplateInput,
    ) -> SaveTemplateOutput:
        """Create and persist a new template.

        Args:
            input_dto: Input parameters for saving a template.

        Returns:
            Output containing the id of the newly created template.
        """
        now = datetime.now(UTC)
        template_name = TemplateName(input_dto.name)
        agenda_templates = [AgendaTemplate(t) for t in input_dto.agenda_topics]

        template = Template.create(
            organizer_id=input_dto.organizer_id,
            name=template_name,
            default_counterparts=input_dto.default_counterpart_ids,
            agenda_templates=agenda_templates,
            now=now,
        )

        events: list[DomainEvent] = []

        async with self._uow:
            await self._template_repo.save(template)
            events = list(template.collect_events())
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return SaveTemplateOutput(template_id=template.id)
