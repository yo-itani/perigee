"""Use case: List all templates owned by an organizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import TemplateId
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class TemplateListItem:
    """A single item in the template list."""

    template_id: TemplateId
    name: str
    default_counterpart_ids: list[UserId]
    agenda_topics: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ListTemplatesInput:
    """Input DTO for ListTemplatesService."""

    actor_id: UserId


@dataclass(frozen=True)
class ListTemplatesOutput:
    """Output DTO for ListTemplatesService."""

    templates: list[TemplateListItem]


class ListTemplatesService:
    """Application service that lists all templates for an organizer.

    This is a read-only operation; no UoW or event dispatching is needed.
    """

    def __init__(
        self,
        template_repo: TemplateRepository,
    ) -> None:
        self._template_repo = template_repo

    async def execute(
        self,
        input_dto: ListTemplatesInput,
    ) -> ListTemplatesOutput:
        """List all templates owned by the actor.

        The actor can only list their own templates.

        Args:
            input_dto: Input containing the actor ID.

        Returns:
            Output containing the list of templates.
        """
        templates = await self._template_repo.list_by_organizer(input_dto.actor_id)

        items = [
            TemplateListItem(
                template_id=t.id,
                name=t.name.value,
                default_counterpart_ids=t.default_counterparts,
                agenda_topics=[at.topic.value for at in t.agenda_templates],
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in templates
        ]

        return ListTemplatesOutput(templates=items)
