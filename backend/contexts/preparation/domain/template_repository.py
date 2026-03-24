from __future__ import annotations

from abc import abstractmethod

from contexts.preparation.domain.template import Template
from contexts.preparation.domain.value_objects import TemplateId
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class TemplateRepository(BaseRepository[Template, TemplateId]):
    """Repository interface for Template aggregates."""

    @abstractmethod
    async def list_by_organizer(self, organizer_id: UserId) -> list[Template]:
        """Return all templates owned by the given organizer."""
