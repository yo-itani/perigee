"""FastAPI router for notification-settings endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from contexts.notification.application.get_notification_setting import (
    GetNotificationSettingInput,
    GetNotificationSettingUseCase,
)
from contexts.notification.application.update_notification_setting import (
    UpdateNotificationSettingInput,
    UpdateNotificationSettingUseCase,
)
from contexts.notification.presentation.dependencies import (
    get_get_notification_setting_service,
    get_update_notification_setting_service,
)
from contexts.notification.presentation.schemas import (
    NotificationSettingResponse,
    UpdateNotificationSettingRequest,
)
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

router = APIRouter(
    prefix="/notification-settings",
    tags=["notification-settings"],
)


@router.get("", response_model=NotificationSettingResponse)
async def get_notification_setting(
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        GetNotificationSettingUseCase,
        Depends(get_get_notification_setting_service),
    ],
) -> NotificationSettingResponse:
    """Get the current user's notification setting."""
    output = await service.execute(
        GetNotificationSettingInput(
            user_id=current_user_id,
            actor_id=current_user_id,
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
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        UpdateNotificationSettingUseCase,
        Depends(get_update_notification_setting_service),
    ],
) -> NotificationSettingResponse:
    """Update the current user's notification setting."""
    output = await service.execute(
        UpdateNotificationSettingInput(
            user_id=current_user_id,
            actor_id=current_user_id,
            reminder_minutes_before=body.reminder_minutes_before,
            is_enabled=body.is_enabled,
        )
    )
    return NotificationSettingResponse(
        user_id=output.user_id.value,
        reminder_minutes_before=output.reminder_minutes_before,
        is_enabled=output.is_enabled,
    )
