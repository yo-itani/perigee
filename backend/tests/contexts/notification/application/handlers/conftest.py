"""Test fixtures for notification handler tests."""

from __future__ import annotations

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import ScheduleGroupId, ScheduleId
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId


class SpyNotificationSender(NotificationSender):
    """Spy that records sent notifications."""

    def __init__(self, *, fail_for: set[UserId] | None = None) -> None:
        self.sent: list[tuple[UserId, NotificationMessage]] = []
        self._fail_for = fail_for or set()

    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        if recipient_id in self._fail_for:
            raise RuntimeError(f"Simulated send failure for {recipient_id}")
        self.sent.append((recipient_id, message))

    @property
    def sent_recipient_ids(self) -> list[UserId]:
        return [r for r, _ in self.sent]


class InMemoryNotificationSettingRepository(NotificationSettingRepository):
    """In-memory stub for NotificationSettingRepository.

    All users are enabled by default unless explicitly disabled.
    Uses get_by_user_id to back the base class's is_enabled() default impl.
    """

    def __init__(self, *, disabled_users: set[UserId] | None = None) -> None:
        self._disabled_users = disabled_users or set()

    async def get_by_user_id(self, user_id: UserId) -> NotificationSetting | None:
        if user_id in self._disabled_users:
            setting = NotificationSetting.create_default(user_id)
            setting.update(
                reminder_minutes_before=setting.reminder_minutes_before,
                is_enabled=False,
                now=setting.created_at,
            )
            setting.collect_events()  # discard
            return setting
        return None  # default behavior: enabled

    async def save(self, entity: NotificationSetting) -> None:
        pass  # not needed for handler tests


class InMemoryScheduleRepository(ScheduleRepository):
    """In-memory stub for ScheduleRepository (notification tests)."""

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


class InMemoryRecordRepository(RecordRepository):
    """In-memory stub for RecordRepository (notification tests)."""

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

    def add(self, record: Record) -> None:
        """Pre-populate a record for testing."""
        self._records[record.id] = record
