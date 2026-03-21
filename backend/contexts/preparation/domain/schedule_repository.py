from abc import ABC, abstractmethod

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import ScheduleId


class ScheduleRepository(ABC):
    """Interface for Schedule aggregate persistence."""

    @abstractmethod
    async def find_by_id(self, schedule_id: ScheduleId) -> Schedule | None:
        """Retrieve a Schedule by its ID, or None if not found."""
        ...

    @abstractmethod
    async def save(self, schedule: Schedule) -> None:
        """Persist a Schedule (insert or update)."""
        ...
