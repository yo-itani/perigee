"""Tests for slack_message_builder."""

from __future__ import annotations

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.value_objects import NotificationType
from contexts.notification.infrastructure.slack_message_builder import (
    build_slack_blocks,
)


class TestBuildSlackBlocks:
    """Tests for build_slack_blocks function."""

    def test_schedule_created_message(self) -> None:
        """Schedule created message includes calendar emoji and header."""
        msg = NotificationMessage(
            notification_type=NotificationType.SCHEDULE_CREATED,
            title="New 1on1 scheduled",
            body="Alice scheduled a 1on1 with you on 2026-04-01.",
        )

        payload = build_slack_blocks(msg)

        blocks = payload["blocks"]
        assert len(blocks) == 2
        assert blocks[0]["type"] == "header"
        assert ":calendar:" in blocks[0]["text"]["text"]
        assert "New 1on1 scheduled" in blocks[0]["text"]["text"]
        assert blocks[1]["type"] == "section"
        assert blocks[1]["text"]["text"] == msg.body

    def test_schedule_rescheduled_message(self) -> None:
        """Schedule rescheduled message uses arrows emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.SCHEDULE_RESCHEDULED,
            title="1on1 rescheduled",
            body="The 1on1 has been moved to 2026-04-02.",
        )

        payload = build_slack_blocks(msg)
        assert ":arrows_counterclockwise:" in payload["blocks"][0]["text"]["text"]

    def test_schedule_cancelled_message(self) -> None:
        """Schedule cancelled message uses no_entry_sign emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.SCHEDULE_CANCELLED,
            title="1on1 cancelled",
            body="The 1on1 on 2026-04-01 has been cancelled.",
        )

        payload = build_slack_blocks(msg)
        assert ":no_entry_sign:" in payload["blocks"][0]["text"]["text"]

    def test_record_published_message(self) -> None:
        """Record published message uses memo emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.RECORD_PUBLISHED,
            title="Record published",
            body="A new record has been published.",
        )

        payload = build_slack_blocks(msg)
        assert ":memo:" in payload["blocks"][0]["text"]["text"]

    def test_agenda_comment_added_message(self) -> None:
        """Agenda comment message uses speech_balloon emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.AGENDA_COMMENT_ADDED,
            title="New agenda comment",
            body="Bob commented on an agenda item.",
        )

        payload = build_slack_blocks(msg)
        assert ":speech_balloon:" in payload["blocks"][0]["text"]["text"]

    def test_record_comment_added_message(self) -> None:
        """Record comment message uses speech_balloon emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.RECORD_COMMENT_ADDED,
            title="New record comment",
            body="Carol commented on a record.",
        )

        payload = build_slack_blocks(msg)
        assert ":speech_balloon:" in payload["blocks"][0]["text"]["text"]

    def test_reminder_message(self) -> None:
        """Reminder message uses bell emoji."""
        msg = NotificationMessage(
            notification_type=NotificationType.REMINDER,
            title="Upcoming 1on1 reminder",
            body="Your 1on1 starts in 30 minutes.",
        )

        payload = build_slack_blocks(msg)
        assert ":bell:" in payload["blocks"][0]["text"]["text"]

    def test_message_with_link_includes_button(self) -> None:
        """Message with a link includes an actions block with a button."""
        msg = NotificationMessage(
            notification_type=NotificationType.RECORD_PUBLISHED,
            title="Record published",
            body="A new record has been published.",
            link="https://app.example.com/records/123",
        )

        payload = build_slack_blocks(msg)

        blocks = payload["blocks"]
        assert len(blocks) == 3
        actions_block = blocks[2]
        assert actions_block["type"] == "actions"
        button = actions_block["elements"][0]
        assert button["type"] == "button"
        assert button["url"] == "https://app.example.com/records/123"
        assert button["text"]["text"] == "Open in perigee"

    def test_message_without_link_has_no_actions_block(self) -> None:
        """Message without a link has only header and section blocks."""
        msg = NotificationMessage(
            notification_type=NotificationType.REMINDER,
            title="Reminder",
            body="Your 1on1 is coming up.",
            link=None,
        )

        payload = build_slack_blocks(msg)

        blocks = payload["blocks"]
        assert len(blocks) == 2
        assert all(b["type"] in ("header", "section") for b in blocks)
