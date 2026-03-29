"""Tests for NotificationRecord domain entity."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.value_objects import NotificationType
from shared.domain.value_objects import UserId


def _make_message(
    *,
    notification_type: NotificationType = NotificationType.SCHEDULE_CREATED,
    title: str = "Test notification",
    body: str = "Test body",
    link: str | None = None,
) -> NotificationMessage:
    return NotificationMessage(
        notification_type=notification_type,
        title=title,
        body=body,
        link=link,
    )


class TestCreate:
    """Tests for NotificationRecord.create."""

    def test_creates_unread_record(self) -> None:
        recipient = UserId.generate()
        message = _make_message()
        now = datetime(2026, 3, 26, 10, 0)

        record = NotificationRecord.create(
            recipient_id=recipient,
            message=message,
            now=now,
        )

        assert record.recipient_id == recipient
        assert record.notification_type == NotificationType.SCHEDULE_CREATED
        assert record.title == "Test notification"
        assert record.body == "Test body"
        assert record.link is None
        assert record.is_read is False
        assert record.read_at is None
        assert record.created_at == now

    def test_creates_with_link(self) -> None:
        message = _make_message(link="/schedules/123")
        record = NotificationRecord.create(
            recipient_id=UserId.generate(),
            message=message,
        )

        assert record.link == "/schedules/123"

    def test_creates_with_different_types(self) -> None:
        for ntype in NotificationType:
            message = _make_message(notification_type=ntype)
            record = NotificationRecord.create(
                recipient_id=UserId.generate(),
                message=message,
            )
            assert record.notification_type == ntype


class TestMarkAsRead:
    """Tests for NotificationRecord.mark_as_read."""

    def test_marks_as_read(self) -> None:
        record = NotificationRecord.create(
            recipient_id=UserId.generate(),
            message=_make_message(),
            now=datetime(2026, 3, 26, 10, 0),
        )
        read_at = datetime(2026, 3, 26, 11, 0)

        record.mark_as_read(now=read_at)

        assert record.is_read is True
        assert record.read_at == read_at

    def test_idempotent_when_already_read(self) -> None:
        record = NotificationRecord.create(
            recipient_id=UserId.generate(),
            message=_make_message(),
        )
        first_read_at = datetime(2026, 3, 26, 11, 0)
        record.mark_as_read(now=first_read_at)

        # Second call is a no-op — no error, read_at unchanged
        record.mark_as_read(now=datetime(2026, 3, 26, 12, 0))

        assert record.is_read is True
        assert record.read_at == first_read_at
