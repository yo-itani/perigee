from __future__ import annotations

from abc import abstractmethod
from datetime import datetime

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import (
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
)
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class ScheduleRepository(BaseRepository[Schedule, ScheduleId]):
    """Repository interface for Schedule aggregates."""

    @abstractmethod
    async def get_by_schedule_group_id(
        self, schedule_group_id: ScheduleGroupId
    ) -> list[Schedule]:
        """Return all schedules belonging to the given schedule group."""

    @abstractmethod
    async def list_upcoming_by_participant(
        self,
        user_id: UserId,
        now: datetime,
        statuses: list[ScheduleStatus],
        limit: int,
    ) -> list[Schedule]:
        """Return upcoming schedules where the user is organizer or counterpart.

        Only schedules with ``scheduled_at >= now`` and matching one of the
        given *statuses* are returned, ordered by ``scheduled_at`` ascending.
        """
