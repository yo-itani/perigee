"""DI providers for the Notification context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.notification.application.get_notification_setting import (
    GetNotificationSettingUseCase,
)
from contexts.notification.application.update_notification_setting import (
    UpdateNotificationSettingUseCase,
)
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.infrastructure.sqlalchemy_notification_setting_repository import (  # noqa: E501
    SqlAlchemyNotificationSettingRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher


def get_notification_setting_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationSettingRepository:
    """Provide a NotificationSettingRepository backed by the current DB session."""
    return SqlAlchemyNotificationSettingRepository(session)


def get_get_notification_setting_service(
    repo: Annotated[
        NotificationSettingRepository, Depends(get_notification_setting_repository)
    ],
) -> GetNotificationSettingUseCase:
    """Provide a GetNotificationSettingUseCase with all dependencies injected."""
    return GetNotificationSettingUseCase(
        notification_setting_repository=repo,
    )


def get_update_notification_setting_service(
    repo: Annotated[
        NotificationSettingRepository, Depends(get_notification_setting_repository)
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> UpdateNotificationSettingUseCase:
    """Provide an UpdateNotificationSettingUseCase with all dependencies injected."""
    return UpdateNotificationSettingUseCase(
        notification_setting_repository=repo,
        unit_of_work=uow,
        event_dispatcher=dispatcher,
    )
