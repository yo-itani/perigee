"""Test fixtures for record application layer tests."""

from __future__ import annotations

from types import TracebackType

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleId
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.comment import Comment
from contexts.record.domain.comment_repository import CommentRepository
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import (
    ActionItemId,
    CommentId,
    RecordId,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class InMemoryRecordRepository(RecordRepository):
    """In-memory stub for RecordRepository."""

    def __init__(self) -> None:
        self._records: dict[RecordId, Record] = {}

    async def get_by_id(self, entity_id: RecordId) -> Record | None:
        return self._records.get(entity_id)

    async def save(self, entity: Record) -> None:
        self._records[entity.id] = entity

    async def exists_by_participant(
        self, user_id: UserId, counterpart_id: UserId
    ) -> bool:
        return any(
            r.counterpart_id == counterpart_id
            and (r.organizer_id == user_id or r.counterpart_id == user_id)
            for r in self._records.values()
        )

    async def list_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
        offset: int,
        limit: int,
    ) -> list[Record]:
        visible = self._visible_published_for_pair(
            actor_id, organizer_id, counterpart_id
        )
        visible.sort(key=lambda r: (r.conducted_at, r.created_at), reverse=True)
        return visible[offset : offset + limit]

    async def count_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> int:
        return len(
            self._visible_published_for_pair(actor_id, organizer_id, counterpart_id)
        )

    async def get_latest_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> Record | None:
        visible = self._visible_published_for_pair(
            actor_id, organizer_id, counterpart_id
        )
        if not visible:
            return None
        visible.sort(key=lambda r: (r.conducted_at, r.created_at), reverse=True)
        return visible[0]

    def _visible_published_for_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> list[Record]:
        from contexts.record.domain.value_objects import RecordStatus

        return [
            r
            for r in self._records.values()
            if r.organizer_id == organizer_id
            and r.counterpart_id == counterpart_id
            and r.status == RecordStatus.PUBLISHED
            and r.is_visible_to(actor_id)
        ]

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

    async def list_pending_by_counterpart(
        self, counterpart_id: UserId, *, limit: int = 50
    ) -> list[ActionItem]:
        pending = [
            item
            for item in self._items.values()
            if item.counterpart_id == counterpart_id and not item.is_completed
        ]
        pending.sort(key=lambda item: item.created_at)
        return pending[: max(0, limit)]

    async def list_by_record_id(self, record_id: RecordId) -> list[ActionItem]:
        items = [item for item in self._items.values() if item.record_id == record_id]
        items.sort(key=lambda item: item.created_at)
        return items

    @property
    def saved_items(self) -> list[ActionItem]:
        return list(self._items.values())


class InMemoryCommentRepository(CommentRepository):
    """In-memory stub for CommentRepository."""

    def __init__(self) -> None:
        self._comments: dict[CommentId, Comment] = {}

    async def get_by_id(self, entity_id: CommentId) -> Comment | None:
        return self._comments.get(entity_id)

    async def save(self, entity: Comment) -> None:
        self._comments[entity.id] = entity

    @property
    def saved_comments(self) -> list[Comment]:
        return list(self._comments.values())


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
