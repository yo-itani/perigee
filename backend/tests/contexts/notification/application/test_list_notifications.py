"""Tests for ListNotificationsUseCase."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.application.list_notifications import (
    ListNotificationsInput,
    ListNotificationsUseCase,
)
from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.value_objects import NotificationType
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.conftest import (
    InMemoryNotificationRecordRepository,
)


def _make_message(
    notification_type: NotificationType = NotificationType.SCHEDULE_CREATED,
) -> NotificationMessage:
    return NotificationMessage(
        notification_type=notification_type,
        title="Test",
        body="Test body",
    )


def _build_use_case(
    *,
    repo: InMemoryNotificationRecordRepository | None = None,
) -> tuple[ListNotificationsUseCase, InMemoryNotificationRecordRepository]:
    r = repo or InMemoryNotificationRecordRepository()
    uc = ListNotificationsUseCase(notification_record_repository=r)
    return uc, r


class TestListNotifications:
    """Tests for listing notifications."""

    async def test_returns_empty_list_when_no_notifications(self) -> None:
        uc, _repo = _build_use_case()
        user_id = UserId.generate()

        output = await uc.execute(ListNotificationsInput(actor_id=user_id))

        assert output.notifications == []

    async def test_returns_all_notifications_for_user(self) -> None:
        uc, repo = _build_use_case()
        user_id = UserId.generate()

        record1 = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(),
            now=datetime(2026, 3, 26, 10, 0),
        )
        record2 = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(NotificationType.RECORD_PUBLISHED),
            now=datetime(2026, 3, 26, 11, 0),
        )
        await repo.save(record1)
        await repo.save(record2)

        output = await uc.execute(ListNotificationsInput(actor_id=user_id))

        assert len(output.notifications) == 2

    async def test_does_not_return_other_users_notifications(self) -> None:
        uc, repo = _build_use_case()
        user_id = UserId.generate()
        other_id = UserId.generate()

        record = NotificationRecord.create(
            recipient_id=other_id,
            message=_make_message(),
        )
        await repo.save(record)

        output = await uc.execute(ListNotificationsInput(actor_id=user_id))

        assert output.notifications == []

    async def test_returns_only_unread_when_filter_set(self) -> None:
        uc, repo = _build_use_case()
        user_id = UserId.generate()

        unread = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(),
            now=datetime(2026, 3, 26, 10, 0),
        )
        read = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(NotificationType.RECORD_PUBLISHED),
            now=datetime(2026, 3, 26, 11, 0),
        )
        read.mark_as_read(now=datetime(2026, 3, 26, 12, 0))

        await repo.save(unread)
        await repo.save(read)

        output = await uc.execute(
            ListNotificationsInput(actor_id=user_id, unread_only=True)
        )

        assert len(output.notifications) == 1
        assert output.notifications[0].is_read is False

    async def test_returns_all_when_filter_not_set(self) -> None:
        uc, repo = _build_use_case()
        user_id = UserId.generate()

        unread = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(),
            now=datetime(2026, 3, 26, 10, 0),
        )
        read = NotificationRecord.create(
            recipient_id=user_id,
            message=_make_message(NotificationType.RECORD_PUBLISHED),
            now=datetime(2026, 3, 26, 11, 0),
        )
        read.mark_as_read(now=datetime(2026, 3, 26, 12, 0))

        await repo.save(unread)
        await repo.save(read)

        output = await uc.execute(
            ListNotificationsInput(actor_id=user_id, unread_only=False)
        )

        assert len(output.notifications) == 2

    async def test_output_contains_correct_fields(self) -> None:
        uc, repo = _build_use_case()
        user_id = UserId.generate()

        record = NotificationRecord.create(
            recipient_id=user_id,
            message=NotificationMessage(
                notification_type=NotificationType.SCHEDULE_CREATED,
                title="New 1-on-1",
                body="A new meeting was scheduled.",
                link="/schedules/abc",
            ),
            now=datetime(2026, 3, 26, 10, 0),
        )
        await repo.save(record)

        output = await uc.execute(ListNotificationsInput(actor_id=user_id))

        n = output.notifications[0]
        assert n.id == record.id.value
        assert n.recipient_id == user_id
        assert n.notification_type == NotificationType.SCHEDULE_CREATED
        assert n.title == "New 1-on-1"
        assert n.body == "A new meeting was scheduled."
        assert n.link == "/schedules/abc"
        assert n.is_read is False
        assert n.read_at is None
        assert n.created_at == datetime(2026, 3, 26, 10, 0)
