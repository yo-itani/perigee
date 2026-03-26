"""Build Slack Block Kit messages from NotificationMessage."""

from __future__ import annotations

from typing import Any

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.value_objects import NotificationType

# Emoji mapping per notification type
_TYPE_EMOJI: dict[NotificationType, str] = {
    NotificationType.SCHEDULE_CREATED: ":calendar:",
    NotificationType.SCHEDULE_RESCHEDULED: ":arrows_counterclockwise:",
    NotificationType.SCHEDULE_CANCELLED: ":no_entry_sign:",
    NotificationType.RECORD_PUBLISHED: ":memo:",
    NotificationType.AGENDA_COMMENT_ADDED: ":speech_balloon:",
    NotificationType.RECORD_COMMENT_ADDED: ":speech_balloon:",
    NotificationType.REMINDER: ":bell:",
}


def build_slack_blocks(message: NotificationMessage) -> dict[str, Any]:
    """Convert a NotificationMessage to a Slack Block Kit payload.

    Returns a dict suitable for posting to a Slack Incoming Webhook URL.
    The payload uses Block Kit for rich formatting.
    """
    emoji = _TYPE_EMOJI.get(message.notification_type, ":loudspeaker:")

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {message.title}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message.body,
            },
        },
    ]

    if message.link:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open in perigee",
                            "emoji": True,
                        },
                        "url": message.link,
                        "action_id": "open_link",
                    }
                ],
            }
        )

    return {"blocks": blocks}
