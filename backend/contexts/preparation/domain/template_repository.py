from __future__ import annotations

from contexts.preparation.domain.template import Template
from contexts.preparation.domain.value_objects import TemplateId
from foundation.domain.base_repository import BaseRepository


class TemplateRepository(BaseRepository[Template, TemplateId]):
    """Repository interface for Template aggregates."""

    pass
