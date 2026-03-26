from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class GetMyProfileOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class GetMyProfileQueryService:
    """Return the current user's profile."""

    def execute(self, user: User) -> GetMyProfileOutput:
        return GetMyProfileOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
