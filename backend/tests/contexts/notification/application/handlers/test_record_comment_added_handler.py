"""Tests for RecordCommentAddedHandler."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.application.handlers.record_comment_added_handler import (
    RecordCommentAddedHandler,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.record.domain.events import RecordCommentAdded
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import CommentId, RecordId
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
    RecordCommentAddedHandler,
    InMemoryRecordRepository,
    SpyNotificationSender,
]:
    rr = record_repo or InMemoryRecordRepository()
    sn = sender or SpyNotificationSender()
    st = setting_repo or InMemoryNotificationSettingRepository()
    handler = RecordCommentAddedHandler(
        record_repository=rr,
        notification_sender=sn,
        notification_setting_repository=st,
    )
    return handler, rr, sn


class TestRecordCommentAddedByPrincipal:
    """When organizer or counterpart comments, notify only the other party."""

    async def test_organizer_comments_notifies_counterpart_only(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=organizer,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [counterpart]
        assert viewer not in sn.sent_recipient_ids
        assert sn.sent[0][1].notification_type == NotificationType.RECORD_COMMENT_ADDED

    async def test_counterpart_comments_notifies_organizer_only(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=counterpart,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [organizer]
        assert viewer not in sn.sent_recipient_ids


class TestRecordCommentAddedByViewer:
    """When a viewer comments, notify both organizer and counterpart."""

    async def test_viewer_comments_notifies_organizer_and_counterpart(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=viewer,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [organizer, counterpart]

    async def test_viewer_is_not_notified_of_own_comment(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        handler, rr, sn = _build_handler()
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=viewer,
            occurred_at=NOW,
        )
        await handler(event)

        assert viewer not in sn.sent_recipient_ids


class TestRecordCommentAddedEdgeCases:
    """Edge cases and error handling."""

    async def test_skips_disabled_recipient(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer, counterpart)

        setting_repo = InMemoryNotificationSettingRepository(
            disabled_users={counterpart}
        )
        handler, rr, sn = _build_handler(setting_repo=setting_repo)
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=organizer,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent == []

    async def test_viewer_comments_skips_disabled_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        setting_repo = InMemoryNotificationSettingRepository(disabled_users={organizer})
        handler, rr, sn = _build_handler(setting_repo=setting_repo)
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=viewer,
            occurred_at=NOW,
        )
        await handler(event)

        # Only counterpart should be notified
        assert sn.sent_recipient_ids == [counterpart]

    async def test_logs_on_record_not_found(self) -> None:
        handler, _rr, sn = _build_handler()

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=RecordId.generate(),
            author_id=UserId.generate(),
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent == []

    async def test_send_failure_does_not_block_other_recipients(self) -> None:
        """If sending to organizer fails, counterpart still gets notified."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer, counterpart, viewers=[viewer])

        sender = SpyNotificationSender(fail_for={organizer})
        handler, rr, _sn = _build_handler(sender=sender)
        rr.add(record)

        event = RecordCommentAdded(
            comment_id=CommentId.generate(),
            record_id=record.id,
            author_id=viewer,
            occurred_at=NOW,
        )
        await handler(event)

        # counterpart should still be notified despite organizer failure
        assert sender.sent_recipient_ids == [counterpart]
