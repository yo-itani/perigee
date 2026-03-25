"""Tests for RecordingNotificationSender."""

from __future__ import annotations

import pytest

from contexts.notification.application.recording_notification_sender import (
    RecordingNotificationSender,
)
from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.value_objects import NotificationType
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.conftest import (
    InMemoryNotificationRecordRepository,
)


class SpyNotificationSender(NotificationSender):
    """Spy sender that records calls."""

    def __init__(self) -> None:
        self.sent: list[tuple[UserId, NotificationMessage]] = []

    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        self.sent.append((recipient_id, message))


class FailingNotificationSender(NotificationSender):
    """Sender that always raises."""

    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        raise RuntimeError("send failed")


def _make_message() -> NotificationMessage:
    return NotificationMessage(
        notification_type=NotificationType.RECORD_PUBLISHED,
        title="Test notification",
        body="Test body",
    )


@pytest.fixture
def repo() -> InMemoryNotificationRecordRepository:
    return InMemoryNotificationRecordRepository()


@pytest.fixture
def spy_sender() -> SpyNotificationSender:
    return SpyNotificationSender()


@pytest.fixture
def recording_sender(
    spy_sender: SpyNotificationSender,
    repo: InMemoryNotificationRecordRepository,
) -> RecordingNotificationSender:
    return RecordingNotificationSender(
        inner=spy_sender,
        notification_record_repository=repo,
    )


class TestRecordingNotificationSender:
    """RecordingNotificationSender のテスト。"""

    async def test_saves_record_and_delegates_to_inner(
        self,
        recording_sender: RecordingNotificationSender,
        spy_sender: SpyNotificationSender,
        repo: InMemoryNotificationRecordRepository,
    ) -> None:
        """送信時に NotificationRecord が保存され、内部 sender に委譲される。"""
        user_id = UserId.generate()
        message = _make_message()

        await recording_sender.send(user_id, message)

        # inner sender に委譲されている
        assert len(spy_sender.sent) == 1
        assert spy_sender.sent[0] == (user_id, message)

        # NotificationRecord が保存されている
        records = await repo.list_by_recipient(user_id)
        assert len(records) == 1
        assert records[0].recipient_id == user_id
        assert records[0].notification_type == NotificationType.RECORD_PUBLISHED
        assert records[0].title == "Test notification"
        assert records[0].is_read is False

    async def test_record_is_saved_even_when_inner_raises(
        self,
        repo: InMemoryNotificationRecordRepository,
    ) -> None:
        """内部 sender が例外を投げても NotificationRecord は保存されている。"""
        user_id = UserId.generate()
        message = _make_message()

        sender = RecordingNotificationSender(
            inner=FailingNotificationSender(),
            notification_record_repository=repo,
        )

        with pytest.raises(RuntimeError, match="send failed"):
            await sender.send(user_id, message)

        # Record は保存されている
        records = await repo.list_by_recipient(user_id)
        assert len(records) == 1

    async def test_multiple_sends_create_separate_records(
        self,
        recording_sender: RecordingNotificationSender,
        repo: InMemoryNotificationRecordRepository,
    ) -> None:
        """複数回の送信でそれぞれ別の NotificationRecord が作成される。"""
        user_id = UserId.generate()
        message = _make_message()

        await recording_sender.send(user_id, message)
        await recording_sender.send(user_id, message)

        records = await repo.list_by_recipient(user_id)
        assert len(records) == 2
        assert records[0].id != records[1].id
