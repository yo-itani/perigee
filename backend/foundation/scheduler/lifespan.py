"""Factory for ReminderScheduler with wired dependencies.

Used by the FastAPI lifespan to create and manage the scheduler.
Returns None if the database is not configured (e.g. in test environments).
"""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_sender import NotificationSender
from foundation.scheduler.reminder_scheduler import ReminderScheduler

logger = logging.getLogger(__name__)


def create_reminder_scheduler() -> ReminderScheduler | None:
    """Create a ReminderScheduler with production dependencies.

    Returns None if construction fails (e.g. missing DB config).
    """
    try:
        service = _SessionScopedReminderService()
        return ReminderScheduler(service)
    except Exception:
        logger.exception("Failed to create ReminderScheduler")
        return None


class _SessionScopedReminderService:
    """Proxy that creates a fresh DB session per scheduler invocation.

    The scheduler runs outside of FastAPI's request lifecycle, so each
    execute() call creates its own session and wires up repositories
    and the SendReminderUseCase.
    """

    async def execute(self, now: object) -> None:
        """Create dependencies and delegate to SendReminderUseCase."""
        from datetime import datetime as dt

        from contexts.notification.application.send_reminder_use_case import (
            SendReminderUseCase,
        )
        from contexts.notification.infrastructure.sqlalchemy_notification_setting_repository import (  # noqa: E501
            SqlAlchemyNotificationSettingRepository,
        )
        from contexts.notification.infrastructure.sqlalchemy_reminder_log_repository import (  # noqa: E501
            SqlAlchemyReminderLogRepository,
        )
        from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
            SqlAlchemyScheduleRepository,
        )
        from foundation.db.session import async_session_factory

        assert isinstance(now, dt)

        async with async_session_factory() as session:
            service = SendReminderUseCase(
                schedule_repository=SqlAlchemyScheduleRepository(session),
                notification_setting_repository=SqlAlchemyNotificationSettingRepository(
                    session
                ),
                reminder_log_repository=SqlAlchemyReminderLogRepository(session),
                notification_sender=_get_recording_notification_sender(session),
            )
            await service.execute(now)
            await session.commit()


def get_base_notification_sender() -> NotificationSender:
    """Get the base NotificationSender implementation.

    Returns a log-only sender until Slack integration is configured.
    """
    from contexts.notification.domain.notification_message import NotificationMessage
    from shared.domain.value_objects import UserId

    class LogOnlyNotificationSender(NotificationSender):
        """Placeholder sender that logs instead of sending."""

        async def send(
            self, recipient_id: UserId, message: NotificationMessage
        ) -> None:
            logger.info(
                "Reminder notification for user %s: %s",
                recipient_id,
                message.title,
            )

    return LogOnlyNotificationSender()


def _get_recording_notification_sender(
    session: object,
) -> NotificationSender:
    """Wrap the base sender with RecordingNotificationSender to persist records."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from contexts.notification.application.recording_notification_sender import (
        RecordingNotificationSender,
    )
    from contexts.notification.infrastructure.sqlalchemy_notification_record_repository import (  # noqa: E501
        SqlAlchemyNotificationRecordRepository,
    )

    assert isinstance(session, AsyncSession)
    return RecordingNotificationSender(
        inner=get_base_notification_sender(),
        notification_record_repository=SqlAlchemyNotificationRecordRepository(session),
    )
