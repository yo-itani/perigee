"""Pydantic schemas for the notification-settings endpoints."""

from __future__ import annotations

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
