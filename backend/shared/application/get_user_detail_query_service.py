"""Query service: get a single user's detail."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class GetUserDetailInput:
    user_id: UserId


@dataclass(frozen=True)
class GetUserDetailOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class GetUserDetailQueryService:
    """Return a single user's detail by ID."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, input_dto: GetUserDetailInput) -> GetUserDetailOutput:
        user = await self._user_repo.get_by_id(input_dto.user_id)
        if user is None:
            raise UserNotFoundError(f"User {input_dto.user_id.value} not found")
        return GetUserDetailOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
