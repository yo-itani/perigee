"""Query service: list all users."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class ListUsersOutput:
    users: list[ListUsersItem]


@dataclass(frozen=True)
class ListUsersItem:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class ListUsersQueryService:
    """Return all users in the system."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self) -> ListUsersOutput:
        users = await self._user_repo.list_all()
        return ListUsersOutput(
            users=[
                ListUsersItem(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    role=u.role,
                    is_active=u.is_active,
                    slack_user_id=u.slack_user_id,
                )
                for u in users
            ]
        )
