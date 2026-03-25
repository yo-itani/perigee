"""APScheduler integration for periodic reminder checks.

Uses AsyncIOScheduler with an IntervalTrigger to invoke
the reminder service every minute.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class ReminderServiceProtocol(Protocol):
    """Protocol for the service invoked by the scheduler."""

    async def execute(self, now: datetime) -> None: ...


class ReminderScheduler:
    """Wraps APScheduler to periodically run reminder checks."""

    def __init__(self, service: ReminderServiceProtocol) -> None:
        self._service = service
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Start the scheduler with a 1-minute interval."""
        self._scheduler.add_job(
            self._run,
            trigger=IntervalTrigger(minutes=1),
            id="send_reminders",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("ReminderScheduler started")

    def shutdown(self) -> None:
        """Gracefully shut down the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("ReminderScheduler shut down")

    async def _run(self) -> None:
        """Execute one cycle of reminder processing."""
        now = datetime.now(UTC)
        try:
            await self._service.execute(now)
        except Exception:
            logger.exception("Reminder scheduler cycle failed")
