"""Slack Webhook implementation of NotificationSender."""

from __future__ import annotations

import asyncio
import logging

import httpx

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.infrastructure.slack_message_builder import (
    build_slack_blocks,
)
from shared.domain.value_objects import UserId

logger = logging.getLogger(__name__)

# HTTP status codes eligible for retry
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0
_BACKOFF_MULTIPLIER = 2.0


class SlackNotificationSender(NotificationSender):
    """Send notifications via Slack Incoming Webhook.

    Uses httpx async client. Retries with exponential backoff on transient
    errors (HTTP 5xx, 429, network timeouts).

    Args:
        webhook_url: The Slack Incoming Webhook URL.
        timeout: HTTP request timeout in seconds.
        transport: Optional httpx transport (for testing).
    """

    def __init__(
        self,
        webhook_url: str,
        *,
        timeout: int = 10,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._transport = transport

    async def send(self, recipient_id: UserId, message: NotificationMessage) -> None:
        """Send a Slack message via webhook.

        Args:
            recipient_id: The user to notify (logged but not used for routing
                since webhooks post to a fixed channel).
            message: The notification content.

        Raises:
            SlackSendError: When delivery fails after all retries.
        """
        payload = build_slack_blocks(message)

        last_exception: Exception | None = None
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                client_kwargs: dict[str, object] = {
                    "timeout": httpx.Timeout(self._timeout),
                }
                if self._transport is not None:
                    client_kwargs["transport"] = self._transport

                async with httpx.AsyncClient(**client_kwargs) as client:  # type: ignore[arg-type]
                    response = await client.post(self._webhook_url, json=payload)

                if response.status_code == 200:
                    logger.info(
                        "Slack notification sent for user %s: %s",
                        recipient_id.value,
                        message.title,
                    )
                    return

                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    raise SlackSendError(
                        f"Slack webhook returned non-retryable status "
                        f"{response.status_code}: {response.text}"
                    )

                last_exception = SlackSendError(
                    f"Slack webhook returned {response.status_code} "
                    f"on attempt {attempt}/{_MAX_RETRIES}"
                )
                logger.warning(
                    "Slack webhook returned %d on attempt %d/%d, retrying...",
                    response.status_code,
                    attempt,
                    _MAX_RETRIES,
                )

            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "Slack webhook timed out on attempt %d/%d, retrying...",
                    attempt,
                    _MAX_RETRIES,
                )
            except SlackSendError:
                raise
            except httpx.HTTPError as exc:
                last_exception = exc
                logger.warning(
                    "Slack webhook network error on attempt %d/%d: %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )

            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)
                backoff *= _BACKOFF_MULTIPLIER

        raise SlackSendError(
            f"Slack webhook failed after {_MAX_RETRIES} retries"
        ) from last_exception


class SlackSendError(Exception):
    """Raised when Slack webhook delivery fails."""
