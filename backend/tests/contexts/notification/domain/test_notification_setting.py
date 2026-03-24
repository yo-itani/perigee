"""Tests for NotificationSetting domain entity."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.notification.domain.events import NotificationSettingUpdated
from contexts.notification.domain.exceptions import InvalidReminderMinutesError
from contexts.notification.domain.notification_setting import NotificationSetting
from shared.domain.value_objects import UserId


class TestCreateDefault:
    """Tests for NotificationSetting.create_default."""

    def test_creates_with_default_values(self) -> None:
        user_id = UserId.generate()
        now = datetime(2026, 3, 24, 10, 0)

        setting = NotificationSetting.create_default(user_id, now=now)

        assert setting.user_id == user_id
        assert setting.reminder_minutes_before == 30
        assert setting.is_enabled is True
        assert setting.created_at == now
        assert setting.updated_at == now

    def test_no_events_on_create_default(self) -> None:
        setting = NotificationSetting.create_default(UserId.generate())

        assert setting.collect_events() == []


class TestCreate:
    """Tests for NotificationSetting.create with explicit values."""

    def test_creates_with_explicit_values(self) -> None:
        user_id = UserId.generate()
        now = datetime(2026, 3, 24, 10, 0)

        setting = NotificationSetting.create(
            user_id=user_id,
            reminder_minutes_before=60,
            is_enabled=False,
            now=now,
        )

        assert setting.user_id == user_id
        assert setting.reminder_minutes_before == 60
        assert setting.is_enabled is False

    def test_raises_when_reminder_below_minimum(self) -> None:
        with pytest.raises(InvalidReminderMinutesError, match="between 5 and 1440"):
            NotificationSetting.create(
                user_id=UserId.generate(),
                reminder_minutes_before=4,
                is_enabled=True,
            )

    def test_raises_when_reminder_above_maximum(self) -> None:
        with pytest.raises(InvalidReminderMinutesError, match="between 5 and 1440"):
            NotificationSetting.create(
                user_id=UserId.generate(),
                reminder_minutes_before=1441,
                is_enabled=True,
            )

    def test_accepts_minimum_boundary(self) -> None:
        setting = NotificationSetting.create(
            user_id=UserId.generate(),
            reminder_minutes_before=5,
            is_enabled=True,
        )
        assert setting.reminder_minutes_before == 5

    def test_accepts_maximum_boundary(self) -> None:
        setting = NotificationSetting.create(
            user_id=UserId.generate(),
            reminder_minutes_before=1440,
            is_enabled=True,
        )
        assert setting.reminder_minutes_before == 1440


class TestUpdate:
    """Tests for NotificationSetting.update."""

    def test_updates_values(self) -> None:
        setting = NotificationSetting.create_default(UserId.generate())
        now = datetime(2026, 3, 24, 12, 0)

        setting.update(
            reminder_minutes_before=60,
            is_enabled=False,
            now=now,
        )

        assert setting.reminder_minutes_before == 60
        assert setting.is_enabled is False
        assert setting.updated_at == now

    def test_emits_event(self) -> None:
        user_id = UserId.generate()
        setting = NotificationSetting.create_default(user_id)
        now = datetime(2026, 3, 24, 12, 0)

        setting.update(
            reminder_minutes_before=15,
            is_enabled=True,
            now=now,
        )

        events = setting.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, NotificationSettingUpdated)
        assert event.user_id == user_id
        assert event.reminder_minutes_before == 15
        assert event.is_enabled is True
        assert event.occurred_at == now

    def test_raises_when_reminder_below_minimum(self) -> None:
        setting = NotificationSetting.create_default(UserId.generate())

        with pytest.raises(InvalidReminderMinutesError):
            setting.update(
                reminder_minutes_before=4,
                is_enabled=True,
                now=datetime(2026, 3, 24, 12, 0),
            )

    def test_raises_when_reminder_above_maximum(self) -> None:
        setting = NotificationSetting.create_default(UserId.generate())

        with pytest.raises(InvalidReminderMinutesError):
            setting.update(
                reminder_minutes_before=1441,
                is_enabled=True,
                now=datetime(2026, 3, 24, 12, 0),
            )

    def test_no_event_on_validation_failure(self) -> None:
        """When validation fails, no event should be accumulated."""
        setting = NotificationSetting.create_default(UserId.generate())

        with pytest.raises(InvalidReminderMinutesError):
            setting.update(
                reminder_minutes_before=0,
                is_enabled=True,
                now=datetime(2026, 3, 24, 12, 0),
            )

        assert setting.collect_events() == []


class TestCollectEvents:
    """Tests for collect_events behavior."""

    def test_clears_events_after_collection(self) -> None:
        setting = NotificationSetting.create_default(UserId.generate())
        setting.update(
            reminder_minutes_before=10,
            is_enabled=True,
            now=datetime(2026, 3, 24, 12, 0),
        )

        first = setting.collect_events()
        second = setting.collect_events()

        assert len(first) == 1
        assert len(second) == 0
