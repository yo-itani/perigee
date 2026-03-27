from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

from shared.domain.value_objects import UserRole

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""

    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UpdateMyProfileRequest(BaseModel):
    """Request schema for updating own profile."""

    name: str
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class CreateUserRequest(BaseModel):
    """Request schema for creating a user."""

    name: str
    email: str
    role: UserRole

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class UpdateUserRequest(BaseModel):
    """Request schema for updating a user."""

    name: str
    email: str
    role: UserRole

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class UserListResponse(BaseModel):
    """Response schema for user list."""

    users: list[UserProfileResponse]
    total: int
