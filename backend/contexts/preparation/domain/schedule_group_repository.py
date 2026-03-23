from __future__ import annotations

from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.value_objects import ScheduleGroupId
from foundation.domain.base_repository import BaseRepository


class ScheduleGroupRepository(BaseRepository[ScheduleGroup, ScheduleGroupId]):
    """Repository interface for ScheduleGroup aggregates."""

    pass
