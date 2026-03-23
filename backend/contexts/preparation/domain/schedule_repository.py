from __future__ import annotations

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import ScheduleId
from foundation.domain.base_repository import BaseRepository


class ScheduleRepository(BaseRepository[Schedule, ScheduleId]):
    """Repository interface for Schedule aggregates."""

    pass
