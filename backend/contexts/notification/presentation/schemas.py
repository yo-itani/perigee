"""Pydantic schemas for the notification endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Response schema for GET /notifications."""

    notifications: list[NotificationRecordResponse]
