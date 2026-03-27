"""Query service: list all users."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class ListUsersInput:
    offset: int = 0
    limit: int = 100


@dataclass(frozen=True)
class ListUsersOutput:
    users: list[ListUsersItem]
    total: int


@dataclass(frozen=True)
class ListUsersItem:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class ListUsersQueryService:
    """Return users in the system with pagination."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, input_dto: ListUsersInput | None = None) -> ListUsersOutput:
        dto = input_dto or ListUsersInput()
        users = await self._user_repo.list_all(offset=dto.offset, limit=dto.limit)
        total = await self._user_repo.count_all()
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
            ],
            total=total,
        )
