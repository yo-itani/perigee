"""Use case: Get a specific template by ID."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import TemplateId
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class GetTemplateInput:
    """Input DTO for GetTemplateQueryService."""

    template_id: TemplateId
    actor_id: UserId


@dataclass(frozen=True)
class GetTemplateOutput:
    """Output DTO for GetTemplateQueryService."""

    template_id: TemplateId
    organizer_id: UserId
    name: str
    default_counterpart_ids: list[UserId]
    agenda_topics: list[str]
    created_at: datetime
    updated_at: datetime


class TemplateNotFoundError(Exception):
    """Raised when the requested template does not exist."""

    def __init__(self, message: str = "Template not found.") -> None:
        super().__init__(message)


class UnauthorizedTemplateAccessError(Exception):
    """Raised when the actor is not the template owner."""

    def __init__(
        self, message: str = "Only the template owner can access this template."
    ) -> None:
        super().__init__(message)


class GetTemplateQueryService:
    """Application service that retrieves a single template.

    Only the owning organizer can retrieve a template.
    """

    def __init__(
        self,
        template_repo: TemplateRepository,
    ) -> None:
        self._template_repo = template_repo

    async def execute(
        self,
        input_dto: GetTemplateInput,
    ) -> GetTemplateOutput:
        """Get a template by ID.

        Args:
            input_dto: Input containing the template ID and actor.

        Returns:
            Output containing the template details.

        Raises:
            TemplateNotFoundError: If the template does not exist.
            UnauthorizedTemplateAccessError: If the actor is not the
                template owner.
        """
        template = await self._template_repo.get_by_id(input_dto.template_id)
        if template is None:
            raise TemplateNotFoundError()

        if template.organizer_id != input_dto.actor_id:
            raise UnauthorizedTemplateAccessError()

        return GetTemplateOutput(
            template_id=template.id,
            organizer_id=template.organizer_id,
            name=template.name.value,
            default_counterpart_ids=template.default_counterparts,
            agenda_topics=[at.topic.value for at in template.agenda_templates],
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
