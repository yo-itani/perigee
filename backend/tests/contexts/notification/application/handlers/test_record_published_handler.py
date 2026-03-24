"""Tests for RecordPublishedHandler."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.application.handlers.record_published_handler import (
    RecordPublishedHandler,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.record.domain.events import RecordPublished
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.handlers.conftest import (
    InMemoryNotificationSettingRepository,
    InMemoryRecordRepository,
    SpyNotificationSender,
)

NOW = datetime(2026, 3, 25, 10, 0)
PUBLISH_TIME = datetime(2026, 3, 25, 12, 0)


def _make_published_record(
    organizer: UserId,
    counterpart: UserId,
    viewers: list[UserId] | None = None,
) -> Record:
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=NOW,
    )
    if viewers:
        record.set_viewers(viewer_ids=viewers, actor_id=organizer, now=PUBLISH_TIME)
    record.publish(actor_id=organizer, now=PUBLISH_TIME)
    record.collect_events()
    return record


def _build_handler(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    sender: SpyNotificationSender | None = None,
    setting_repo: InMemoryNotificationSettingRepository | None = None,
) -> tuple[
    RecordPublishedHandler,
    InMemoryRecordRepository,
    SpyNotificationSender,
]:
    rr = record_repo or InMemoryRecordRepository()
    sn = sender or SpyNotificationSender()
    st = setting_repo or InMemoryNotificationSettingRepository()
    handler = RecordPublishedHandler(
        record_repository=rr,
        notification_sender=sn,
        notification_setting_repository=st,
    )
    return handler, rr, sn


class TestRecordPublishedHandler:
    """Tests for RecordPublishedHandler."""

    async def test_notifies_counterpart(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer, counterpart)

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordPublished(
            record_id=record.id,
            organizer_id=organizer,
            occurred_at=PUBLISH_TIME,
        )
        await handler(event)

        assert counterpart in sn.sent_recipient_ids
        assert organizer not in sn.sent_recipient_ids
        assert sn.sent[0][1].notification_type == NotificationType.RECORD_PUBLISHED

    async def test_notifies_counterpart_and_viewers(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer1 = UserId.generate()
        viewer2 = UserId.generate()
        record = _make_published_record(
            organizer, counterpart, viewers=[viewer1, viewer2]
        )

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordPublished(
            record_id=record.id,
            organizer_id=organizer,
            occurred_at=PUBLISH_TIME,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [counterpart, viewer1, viewer2]

    async def test_skips_disabled_recipient(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        setting_repo = InMemoryNotificationSettingRepository(disabled_users={viewer})
        handler, rr, sn = _build_handler(setting_repo=setting_repo)
        rr.add(record)

        event = RecordPublished(
            record_id=record.id,
            organizer_id=organizer,
            occurred_at=PUBLISH_TIME,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [counterpart]

    async def test_logs_on_record_not_found(self) -> None:
        handler, _rr, sn = _build_handler()

        event = RecordPublished(
            record_id=RecordId.generate(),
            organizer_id=UserId.generate(),
            occurred_at=PUBLISH_TIME,
        )
        await handler(event)

        assert sn.sent == []

    async def test_send_failure_does_not_block_other_recipients(self) -> None:
        """If sending to one recipient fails, others still get notified."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        sender = SpyNotificationSender(fail_for={counterpart})
        handler, rr, _sn = _build_handler(sender=sender)
        rr.add(record)

        event = RecordPublished(
            record_id=record.id,
            organizer_id=organizer,
            occurred_at=PUBLISH_TIME,
        )
        # Should not raise
        await handler(event)

        # viewer should still be notified
        assert sender.sent_recipient_ids == [viewer]
