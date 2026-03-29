"""Pydantic schemas for the notification endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class NotificationSettingResponse(BaseModel):
    """Response schema for GET and PUT /notification-settings."""

    user_id: UUID
    reminder_minutes_before: int
    is_enabled: bool


class UpdateNotificationSettingRequest(BaseModel):
    """Request body for PUT /notification-settings."""

    reminder_minutes_before: int
    is_enabled: bool


class NotificationRecordResponse(BaseModel):
    """Response schema for a single notification record."""

    id: UUID
    recipient_id: UUID
    notification_type: str
    title: str
    body: str
    link: str | None
    is_read: bool
    read_at: AwareDatetime | None = Field(
        default=None,
        description="Returned in UTC.",
        json_schema_extra={"example": "2026-03-29T06:30:00Z"},
    )
    created_at: AwareDatetime = Field(
        description="Returned in UTC.",
        json_schema_extra={"example": "2026-03-29T06:30:00Z"},
    )


class NotificationListResponse(BaseModel):
    """Response schema for GET /notifications."""

    notifications: list[NotificationRecordResponse]
