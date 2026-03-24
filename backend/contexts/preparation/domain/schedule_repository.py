from __future__ import annotations

from abc import abstractmethod

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleId
from foundation.domain.base_repository import BaseRepository


class ScheduleRepository(BaseRepository[Schedule, ScheduleId]):
    """Repository interface for Schedule aggregates."""

    @abstractmethod
    async def get_by_schedule_group_id(
        self, schedule_group_id: ScheduleGroupId
    ) -> list[Schedule]:
        """Return all schedules belonging to the given schedule group."""
