from __future__ import annotations

from contexts.record.domain.retrospective import Retrospective
from contexts.record.domain.value_objects import RetrospectiveId
from foundation.domain.base_repository import BaseRepository


class RetrospectiveRepository(BaseRepository[Retrospective, RetrospectiveId]):
    """Repository interface for Retrospective aggregates.

    Retrospective is insert-only: save() must raise an exception
    if the entity already exists.
    """

    pass
