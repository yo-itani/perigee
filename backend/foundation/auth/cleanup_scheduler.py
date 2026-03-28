"""Scheduled job to clean up expired tokens and old login attempts.

Runs daily at 03:00 JST (18:00 UTC) and deletes:
- Expired refresh tokens
- Login attempt records older than 90 days
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 90


class AuthCleanupScheduler:
    """Wraps APScheduler to periodically clean up auth-related records."""

    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        self._scheduler = scheduler

    def register(self) -> None:
        """Register the cleanup job with the scheduler.

        Runs daily at 03:00 JST (= 18:00 UTC previous day).
        """
        self._scheduler.add_job(
            _run_cleanup,
            trigger=CronTrigger(hour=18, minute=0, timezone="UTC"),
            id="auth_cleanup",
            replace_existing=True,
        )
        logger.info("AuthCleanupScheduler registered (daily at 03:00 JST)")


async def _run_cleanup() -> None:
    """Execute one cycle of auth cleanup."""
    from foundation.auth.sqlalchemy_login_attempt_repository import (
        SqlAlchemyLoginAttemptRepository,
    )
    from foundation.auth.sqlalchemy_refresh_token_repository import (
        SqlAlchemyRefreshTokenRepository,
    )
    from foundation.db.session import async_session_factory

    now = datetime.now(UTC)
    login_attempt_cutoff = now - timedelta(days=_RETENTION_DAYS)

    try:
        async with async_session_factory() as session:
            refresh_repo = SqlAlchemyRefreshTokenRepository(session)
            login_repo = SqlAlchemyLoginAttemptRepository(session)

            deleted_tokens = await refresh_repo.delete_expired(now)
            deleted_attempts = await login_repo.delete_older_than(login_attempt_cutoff)

            await session.commit()

            logger.info(
                "Auth cleanup: %d tokens, %d attempts deleted",
                deleted_tokens,
                deleted_attempts,
            )
    except Exception:
        logger.exception("Auth cleanup failed")
