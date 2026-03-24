from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar

from contexts.notification.domain.events import NotificationSettingUpdated
from contexts.notification.domain.exceptions import InvalidReminderMinutesError
from shared.domain.value_objects import UserId

_MIN_REMINDER_MINUTES = 5
_MAX_REMINDER_MINUTES = 1440


@dataclass
class NotificationSetting:
    """Entity: per-user notification setting.

    Business rules:
    - One setting per user (user_id is the identity).
    - reminder_minutes_before must be between 5 and 1440.
    - is_enabled controls whether notifications are active.
    - Default values are used when no DB row exists.
    """

    DEFAULT_REMINDER_MINUTES: ClassVar[int] = 30
    DEFAULT_IS_ENABLED: ClassVar[bool] = True

    user_id: UserId
    _reminder_minutes_before: int
    _is_enabled: bool
    created_at: datetime
    _updated_at: datetime
    _events: list[NotificationSettingUpdated] = field(default_factory=list, repr=False)

    @property
    def reminder_minutes_before(self) -> int:
        return self._reminder_minutes_before

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @staticmethod
    def create_default(
        user_id: UserId, *, now: datetime | None = None
    ) -> NotificationSetting:
        """Create a default setting for a user (not persisted)."""
        ts = now or datetime.now(UTC)
        return NotificationSetting(
            user_id=user_id,
            _reminder_minutes_before=NotificationSetting.DEFAULT_REMINDER_MINUTES,
            _is_enabled=NotificationSetting.DEFAULT_IS_ENABLED,
            created_at=ts,
            _updated_at=ts,
        )

    @staticmethod
    def create(
        *,
        user_id: UserId,
        reminder_minutes_before: int,
        is_enabled: bool,
        now: datetime | None = None,
    ) -> NotificationSetting:
        """Create a new setting with explicit values."""
        NotificationSetting._validate_reminder_minutes(reminder_minutes_before)
        ts = now or datetime.now(UTC)
        return NotificationSetting(
            user_id=user_id,
            _reminder_minutes_before=reminder_minutes_before,
            _is_enabled=is_enabled,
            created_at=ts,
            _updated_at=ts,
        )

    def update(
        self,
        *,
        reminder_minutes_before: int,
        is_enabled: bool,
        now: datetime,
    ) -> None:
        """Update the setting values."""
        self._validate_reminder_minutes(reminder_minutes_before)
        self._reminder_minutes_before = reminder_minutes_before
        self._is_enabled = is_enabled
        self._updated_at = now
        self._events.append(
            NotificationSettingUpdated(
                occurred_at=now,
                user_id=self.user_id,
                reminder_minutes_before=reminder_minutes_before,
                is_enabled=is_enabled,
            )
        )

    def collect_events(self) -> list[NotificationSettingUpdated]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events

    @staticmethod
    def _validate_reminder_minutes(value: int) -> None:
        if value < _MIN_REMINDER_MINUTES or value > _MAX_REMINDER_MINUTES:
            raise InvalidReminderMinutesError(
                f"reminder_minutes_before must be between"
                f" {_MIN_REMINDER_MINUTES} and {_MAX_REMINDER_MINUTES},"
                f" got {value}."
            )
