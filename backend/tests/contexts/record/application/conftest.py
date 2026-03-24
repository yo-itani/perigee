"""Test fixtures for record application layer tests."""

from __future__ import annotations

from types import TracebackType

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleId
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent


class InMemoryRecordRepository(RecordRepository):
    """In-memory stub for RecordRepository."""

    def __init__(self) -> None:
        self._records: dict[RecordId, Record] = {}

    async def get_by_id(self, entity_id: RecordId) -> Record | None:
        return self._records.get(entity_id)

    async def save(self, entity: Record) -> None:
        self._records[entity.id] = entity

    @property
    def saved_records(self) -> list[Record]:
        return list(self._records.values())


class InMemoryActionItemRepository(ActionItemRepository):
    """In-memory stub for ActionItemRepository."""

    def __init__(self) -> None:
        self._items: dict[ActionItemId, ActionItem] = {}

    async def get_by_id(self, entity_id: ActionItemId) -> ActionItem | None:
        return self._items.get(entity_id)

    async def save(self, entity: ActionItem) -> None:
        self._items[entity.id] = entity

    @property
    def saved_items(self) -> list[ActionItem]:
        return list(self._items.values())


class InMemoryScheduleRepository(ScheduleRepository):
    """In-memory stub for ScheduleRepository."""

    def __init__(self) -> None:
        self._schedules: dict[ScheduleId, Schedule] = {}

    async def get_by_id(self, entity_id: ScheduleId) -> Schedule | None:
        return self._schedules.get(entity_id)

    async def save(self, entity: Schedule) -> None:
        self._schedules[entity.id] = entity

    async def get_by_schedule_group_id(
        self, schedule_group_id: ScheduleGroupId
    ) -> list[Schedule]:
        return [
            s
            for s in self._schedules.values()
            if getattr(s, "schedule_group_id", None) == schedule_group_id
        ]

    def add(self, schedule: Schedule) -> None:
        """Pre-populate a schedule for testing."""
        self._schedules[schedule.id] = schedule


class FakeUnitOfWork(UnitOfWork):
    """Fake UnitOfWork that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class SpyEventDispatcher(EventDispatcher):
    """Spy that records dispatched events."""

    def __init__(self) -> None:
        self.dispatched_events: list[DomainEvent] = []

    async def dispatch(self, events: list[DomainEvent]) -> None:
        self.dispatched_events.extend(events)
