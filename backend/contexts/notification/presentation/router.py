"""FastAPI router for notification endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from contexts.notification.application.get_notification_setting import (
    GetNotificationSettingInput,
    GetNotificationSettingUseCase,
)
from contexts.notification.application.list_notifications import (
    ListNotificationsInput,
    ListNotificationsUseCase,
)
from contexts.notification.application.mark_notification_as_read import (
    MarkNotificationAsReadInput,
    MarkNotificationAsReadUseCase,
)
from contexts.notification.application.update_notification_setting import (
    UpdateNotificationSettingInput,
    UpdateNotificationSettingUseCase,
)
from contexts.notification.domain.value_objects import NotificationRecordId
from contexts.notification.presentation.dependencies import (
    get_get_notification_setting_service,
    get_list_notifications_service,
    get_mark_notification_as_read_service,
    get_update_notification_setting_service,
)
from contexts.notification.presentation.schemas import (
    NotificationListResponse,
    NotificationRecordResponse,
    NotificationSettingResponse,
    UpdateNotificationSettingRequest,
)
from foundation.auth.dependencies import get_current_user
from shared.domain.user import User

router = APIRouter(
    prefix="/notification-settings",
    tags=["notification-settings"],
)

notifications_router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get("", response_model=NotificationSettingResponse)
async def get_notification_setting(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        GetNotificationSettingUseCase,
        Depends(get_get_notification_setting_service),
    ],
) -> NotificationSettingResponse:
    """Get the current user's notification setting."""
    output = await service.execute(
        GetNotificationSettingInput(
            user_id=current_user.id,
            actor_id=current_user.id,
        )
    )
    return NotificationSettingResponse(
        user_id=output.user_id.value,
        reminder_minutes_before=output.reminder_minutes_before,
        is_enabled=output.is_enabled,
    )


@router.put("", response_model=NotificationSettingResponse)
async def update_notification_setting(
    body: UpdateNotificationSettingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        UpdateNotificationSettingUseCase,
        Depends(get_update_notification_setting_service),
    ],
) -> NotificationSettingResponse:
    """Update the current user's notification setting."""
    output = await service.execute(
        UpdateNotificationSettingInput(
            user_id=current_user.id,
            actor_id=current_user.id,
            reminder_minutes_before=body.reminder_minutes_before,
            is_enabled=body.is_enabled,
        )
    )
    return NotificationSettingResponse(
        user_id=output.user_id.value,
        reminder_minutes_before=output.reminder_minutes_before,
        is_enabled=output.is_enabled,
    )


@notifications_router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        ListNotificationsUseCase,
        Depends(get_list_notifications_service),
    ],
    unread: bool = False,
) -> NotificationListResponse:
    """List notifications for the current user.

    Query params:
        unread: If true, return only unread notifications.
    """
    output = await service.execute(
        ListNotificationsInput(
            actor_id=current_user.id,
            unread_only=unread,
        )
    )
    return NotificationListResponse(
        notifications=[
            NotificationRecordResponse(
                id=n.id,
                recipient_id=n.recipient_id.value,
                notification_type=n.notification_type.value,
                title=n.title,
                body=n.body,
                link=n.link,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in output.notifications
        ]
    )


@notifications_router.post("/{notification_id}/read", status_code=204)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        MarkNotificationAsReadUseCase,
        Depends(get_mark_notification_as_read_service),
    ],
) -> Response:
    """Mark a notification as read."""
    await service.execute(
        MarkNotificationAsReadInput(
            notification_id=NotificationRecordId(value=notification_id),
            actor_id=current_user.id,
        )
    )
    return Response(status_code=204)
