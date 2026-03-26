"""Test fixtures for notification application layer tests."""

from __future__ import annotations

from types import TracebackType

from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.notification_record_repository import (
    NotificationRecordRepository,
)
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationRecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class InMemoryNotificationRecordRepository(NotificationRecordRepository):
    """In-memory stub for NotificationRecordRepository."""

    def __init__(self) -> None:
        self._records: dict[NotificationRecordId, NotificationRecord] = {}

    async def get_by_id(
        self, record_id: NotificationRecordId
    ) -> NotificationRecord | None:
        return self._records.get(record_id)

    async def list_by_recipient(
        self,
        recipient_id: UserId,
        *,
        unread_only: bool = False,
    ) -> list[NotificationRecord]:
        results = [r for r in self._records.values() if r.recipient_id == recipient_id]
        if unread_only:
            results = [r for r in results if not r.is_read]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    async def save(self, record: NotificationRecord) -> None:
        self._records[record.id] = record


class InMemoryNotificationSettingRepository(NotificationSettingRepository):
    """In-memory stub for NotificationSettingRepository."""

    def __init__(self) -> None:
        self._settings: dict[UserId, NotificationSetting] = {}

    async def get_by_user_id(self, user_id: UserId) -> NotificationSetting | None:
        return self._settings.get(user_id)

    async def save(self, entity: NotificationSetting) -> None:
        self._settings[entity.user_id] = entity

    @property
    def saved_settings(self) -> list[NotificationSetting]:
        return list(self._settings.values())


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
