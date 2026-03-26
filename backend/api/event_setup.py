"""EventDispatcher initialization for the application lifecycle."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DomainEvent)


def _session_scoped_handler(
    handler_factory: Callable[..., Callable[[T], Awaitable[None]]],
) -> Callable[[T], Awaitable[None]]:
    """Wrap a handler factory so each invocation gets a fresh DB session.

    Event handlers need DB access (repositories) but are registered at app
    startup as singletons.  This wrapper creates a fresh session per dispatch,
    instantiates the handler with its dependencies, executes it, and commits.

    This is the same pattern used by the scheduler's _SessionScopedReminderService.
    """

    async def wrapper(event: T) -> None:
        from contexts.notification.application.recording_notification_sender import (
            RecordingNotificationSender,
        )
        from contexts.notification.infrastructure.sqlalchemy_notification_record_repository import (  # noqa: E501
            SqlAlchemyNotificationRecordRepository,
        )
        from contexts.notification.infrastructure.sqlalchemy_notification_setting_repository import (  # noqa: E501
            SqlAlchemyNotificationSettingRepository,
        )
        from foundation.db.session import async_session_factory
        from foundation.scheduler.lifespan import get_base_notification_sender  # noqa: E501

        async with async_session_factory() as session:
            sender = RecordingNotificationSender(
                inner=get_base_notification_sender(),
                notification_record_repository=SqlAlchemyNotificationRecordRepository(
                    session
                ),
            )
            setting_repo = SqlAlchemyNotificationSettingRepository(session)
            handler = handler_factory(
                notification_sender=sender,
                notification_setting_repository=setting_repo,
                session=session,
            )
            try:
                await handler(event)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "Event handler failed for %s", type(event).__name__
                )

    return wrapper


def _make_record_published_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for RecordPublishedHandler."""
    from contexts.notification.application.handlers.record_published_handler import (
        RecordPublishedHandler,
    )
    from contexts.record.infrastructure.sqlalchemy_record_repository import (
        SqlAlchemyRecordRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return RecordPublishedHandler(
        record_repository=SqlAlchemyRecordRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def _make_record_comment_added_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for RecordCommentAddedHandler."""
    from contexts.notification.application.handlers.record_comment_added_handler import (
        RecordCommentAddedHandler,
    )
    from contexts.record.infrastructure.sqlalchemy_record_repository import (
        SqlAlchemyRecordRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return RecordCommentAddedHandler(
        record_repository=SqlAlchemyRecordRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def _make_schedule_created_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for ScheduleCreatedHandler."""
    from contexts.notification.application.handlers.schedule_created_handler import (
        ScheduleCreatedHandler,
    )
    from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
        SqlAlchemyScheduleRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return ScheduleCreatedHandler(
        schedule_repository=SqlAlchemyScheduleRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def _make_schedule_cancelled_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for ScheduleCancelledHandler."""
    from contexts.notification.application.handlers.schedule_cancelled_handler import (
        ScheduleCancelledHandler,
    )
    from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
        SqlAlchemyScheduleRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return ScheduleCancelledHandler(
        schedule_repository=SqlAlchemyScheduleRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def _make_schedule_rescheduled_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for ScheduleRescheduledHandler."""
    from contexts.notification.application.handlers.schedule_rescheduled_handler import (
        ScheduleRescheduledHandler,
    )
    from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
        SqlAlchemyScheduleRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return ScheduleRescheduledHandler(
        schedule_repository=SqlAlchemyScheduleRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def _make_agenda_comment_added_handler(
    *,
    notification_sender: object,
    notification_setting_repository: object,
    session: object,
) -> Callable[..., Awaitable[None]]:
    """Factory for AgendaCommentAddedHandler."""
    from contexts.notification.application.handlers.agenda_comment_added_handler import (
        AgendaCommentAddedHandler,
    )
    from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
        SqlAlchemyScheduleRepository,
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return AgendaCommentAddedHandler(
        schedule_repository=SqlAlchemyScheduleRepository(session),
        notification_sender=notification_sender,  # type: ignore[arg-type]
        notification_setting_repository=notification_setting_repository,  # type: ignore[arg-type]
    )


def create_event_dispatcher() -> object:
    """Create an InMemoryEventDispatcher and register all event handlers.

    This function is called once at application startup.  The returned
    dispatcher is stored on ``app.state`` and shared across all requests.

    Handlers are wrapped with _session_scoped_handler so each dispatch
    creates a fresh DB session with all dependencies (repositories,
    RecordingNotificationSender, etc.).
    """
    from contexts.preparation.domain.events import (
        AgendaCommentAdded,
        ScheduleCancelled,
        ScheduleCreated,
        ScheduleRescheduled,
    )
    from contexts.record.domain.events import RecordCommentAdded, RecordPublished
    from foundation.infrastructure.in_memory_event_dispatcher import (
        InMemoryEventDispatcher,
    )

    dispatcher = InMemoryEventDispatcher()

    # Record context events
    dispatcher.register(
        RecordPublished,
        _session_scoped_handler(_make_record_published_handler),
    )
    dispatcher.register(
        RecordCommentAdded,
        _session_scoped_handler(_make_record_comment_added_handler),
    )

    # Preparation context events
    dispatcher.register(
        ScheduleCreated,
        _session_scoped_handler(_make_schedule_created_handler),
    )
    dispatcher.register(
        ScheduleCancelled,
        _session_scoped_handler(_make_schedule_cancelled_handler),
    )
    dispatcher.register(
        ScheduleRescheduled,
        _session_scoped_handler(_make_schedule_rescheduled_handler),
    )
    dispatcher.register(
        AgendaCommentAdded,
        _session_scoped_handler(_make_agenda_comment_added_handler),
    )

    return dispatcher
