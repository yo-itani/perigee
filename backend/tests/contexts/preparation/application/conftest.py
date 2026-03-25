"""Shared test doubles for preparation application layer tests."""

from __future__ import annotations

from datetime import datetime
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
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
    TemplateId,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId


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

    async def list_upcoming_by_participant(
        self,
        user_id: UserId,
        now: datetime,
        statuses: list[ScheduleStatus],
        limit: int,
    ) -> list[Schedule]:
        matching = [
            s
            for s in self._store.values()
            if (s.organizer_id == user_id or s.counterpart_id == user_id)
            and s.status in statuses
            and s.scheduled_at >= now
        ]
        matching.sort(key=lambda s: s.scheduled_at)
        return matching[:limit]

    async def list_confirmed_upcoming(
        self, now: datetime, lookahead_minutes: int
    ) -> list[Schedule]:
        return []  # not needed for preparation tests

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


class InMemoryTemplateRepository(TemplateRepository):
    """In-memory template repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[TemplateId, Template] = {}

    async def get_by_id(self, entity_id: TemplateId) -> Template | None:
        return self._store.get(entity_id)

    async def save(self, entity: Template) -> None:
        self._store[entity.id] = entity

    async def list_by_organizer(self, organizer_id: UserId) -> list[Template]:
        return [t for t in self._store.values() if t.organizer_id == organizer_id]

    @property
    def templates(self) -> dict[TemplateId, Template]:
        return dict(self._store)


@pytest.fixture
def template_repo() -> InMemoryTemplateRepository:
    return InMemoryTemplateRepository()


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
