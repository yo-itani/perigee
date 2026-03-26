"""Tests for SlackNotificationSender."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import httpx
import pytest

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.value_objects import NotificationType
from contexts.notification.infrastructure.slack_notification_sender import (
    SlackNotificationSender,
    SlackSendError,
)
from shared.domain.value_objects import UserId

WEBHOOK_URL = "https://example.com/slack-webhook-test"


def _make_message(
    *,
    title: str = "Test notification",
    body: str = "Test body",
    link: str | None = None,
) -> NotificationMessage:
    return NotificationMessage(
        notification_type=NotificationType.RECORD_PUBLISHED,
        title=title,
        body=body,
        link=link,
    )


def _user_id() -> UserId:
    return UserId(value=uuid.uuid4())


class TestSlackNotificationSender:
    """Tests for SlackNotificationSender using httpx MockTransport."""

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        """Successful webhook call returns without error."""
        transport = httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        # Should not raise
        await sender.send(_user_id(), _make_message())

    @pytest.mark.asyncio
    async def test_send_posts_json_payload_with_blocks(self) -> None:
        """Webhook request contains Block Kit JSON payload."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, text="ok")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        await sender.send(
            _user_id(), _make_message(link="https://example.com/records/1")
        )

        assert len(captured) == 1
        body = json.loads(captured[0].content)
        assert "blocks" in body
        # header + section + actions (link button)
        assert len(body["blocks"]) == 3

    @pytest.mark.asyncio
    async def test_retry_on_503_then_success(self) -> None:
        """Retries on 503 and succeeds on subsequent attempt."""
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                return httpx.Response(503, text="Service Unavailable")
            return httpx.Response(200, text="ok")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        with patch(
            "contexts.notification.infrastructure.slack_notification_sender.asyncio.sleep",
            return_value=None,
        ):
            await sender.send(_user_id(), _make_message())

        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_429_then_success(self) -> None:
        """Retries on 429 (rate limited) and succeeds."""
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                return httpx.Response(429, text="Rate limited")
            return httpx.Response(200, text="ok")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        with patch(
            "contexts.notification.infrastructure.slack_notification_sender.asyncio.sleep",
            return_value=None,
        ):
            await sender.send(_user_id(), _make_message())

        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self) -> None:
        """Non-retryable HTTP error (400) raises without retry."""
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(400, text="Bad Request")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        with pytest.raises(SlackSendError, match="non-retryable"):
            await sender.send(_user_id(), _make_message())

        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        """Raises SlackSendError after exhausting all retries."""
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        with (
            patch(
                "contexts.notification.infrastructure.slack_notification_sender.asyncio.sleep",
                return_value=None,
            ),
            pytest.raises(SlackSendError, match="failed after 3 retries"),
        ):
            await sender.send(_user_id(), _make_message())

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_timeout_retries_then_fails(self) -> None:
        """Retries on timeout and eventually raises SlackSendError."""
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ReadTimeout("Timed out")

        transport = httpx.MockTransport(handler)
        sender = SlackNotificationSender(
            webhook_url=WEBHOOK_URL, timeout=5, transport=transport
        )

        with (
            patch(
                "contexts.notification.infrastructure.slack_notification_sender.asyncio.sleep",
                return_value=None,
            ),
            pytest.raises(SlackSendError, match="failed after 3 retries"),
        ):
            await sender.send(_user_id(), _make_message())

        assert attempt_count == 3
