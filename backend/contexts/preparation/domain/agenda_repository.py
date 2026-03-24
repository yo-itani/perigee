from __future__ import annotations

from abc import abstractmethod

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from foundation.domain.base_repository import BaseRepository


class AgendaRepository(BaseRepository[Agenda, AgendaId]):
    """Repository interface for Agenda entities."""

    @abstractmethod
    async def get_by_schedule_id(self, schedule_id: ScheduleId) -> list[Agenda]:
        """Return all agendas belonging to the given schedule."""

    @abstractmethod
    async def get_by_schedule_ids(
        self, schedule_ids: list[ScheduleId]
    ) -> dict[ScheduleId, list[Agenda]]:
        """Return agendas grouped by schedule ID for the given schedule IDs."""

    @abstractmethod
    async def save_all(self, agendas: list[Agenda]) -> None:
        """Persist multiple agendas at once (insert or update)."""

    @abstractmethod
    async def delete_by_ids(self, agenda_ids: list[AgendaId]) -> None:
        """Delete agendas by their IDs."""
