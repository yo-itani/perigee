"""Shared test doubles for preparation application layer tests."""

from __future__ import annotations

from types import TracebackType

import pytest

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher


class StubUnitOfWork(UnitOfWork):
    """In-memory UoW that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> StubUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class InMemoryScheduleGroupRepository(ScheduleGroupRepository):
    """In-memory schedule group repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[ScheduleGroupId, ScheduleGroup] = {}

    async def get_by_id(self, entity_id: ScheduleGroupId) -> ScheduleGroup | None:
        return self._store.get(entity_id)

    async def save(self, entity: ScheduleGroup) -> None:
        self._store[entity.id] = entity

    @property
    def groups(self) -> dict[ScheduleGroupId, ScheduleGroup]:
        return dict(self._store)


class InMemoryScheduleRepository(ScheduleRepository):
    """In-memory schedule repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[ScheduleId, Schedule] = {}

    async def get_by_id(self, entity_id: ScheduleId) -> Schedule | None:
        return self._store.get(entity_id)

    async def save(self, entity: Schedule) -> None:
        self._store[entity.id] = entity

    async def get_by_schedule_group_id(
        self, schedule_group_id: ScheduleGroupId
    ) -> list[Schedule]:
        return [
            s for s in self._store.values() if s.schedule_group_id == schedule_group_id
        ]

    @property
    def schedules(self) -> dict[ScheduleId, Schedule]:
        return dict(self._store)


class InMemoryAgendaRepository(AgendaRepository):
    """In-memory agenda repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[AgendaId, Agenda] = {}

    async def get_by_id(self, entity_id: AgendaId) -> Agenda | None:
        return self._store.get(entity_id)

    async def save(self, entity: Agenda) -> None:
        self._store[entity.id] = entity

    async def get_by_schedule_id(self, schedule_id: ScheduleId) -> list[Agenda]:
        return [a for a in self._store.values() if a.schedule_id == schedule_id]

    async def get_by_schedule_ids(
        self, schedule_ids: list[ScheduleId]
    ) -> dict[ScheduleId, list[Agenda]]:
        result: dict[ScheduleId, list[Agenda]] = {sid: [] for sid in schedule_ids}
        for agenda in self._store.values():
            if agenda.schedule_id in result:
                result[agenda.schedule_id].append(agenda)
        return result

    async def save_all(self, agendas: list[Agenda]) -> None:
        for agenda in agendas:
            self._store[agenda.id] = agenda

    async def delete_by_ids(self, agenda_ids: list[AgendaId]) -> None:
        for aid in agenda_ids:
            self._store.pop(aid, None)

    @property
    def agendas(self) -> dict[AgendaId, Agenda]:
        return dict(self._store)


@pytest.fixture
def uow() -> StubUnitOfWork:
    return StubUnitOfWork()


@pytest.fixture
def schedule_group_repo() -> InMemoryScheduleGroupRepository:
    return InMemoryScheduleGroupRepository()


@pytest.fixture
def schedule_repo() -> InMemoryScheduleRepository:
    return InMemoryScheduleRepository()


@pytest.fixture
def agenda_repo() -> InMemoryAgendaRepository:
    return InMemoryAgendaRepository()


@pytest.fixture
def dispatcher() -> InMemoryEventDispatcher:
    return InMemoryEventDispatcher()
