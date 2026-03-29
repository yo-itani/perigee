"""Use case: activate a deactivated user."""

from __future__ import annotations

from dataclasses import dataclass

from foundation.application.unit_of_work import UnitOfWork
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class ActivateUserInput:
    user_id: UserId


@dataclass(frozen=True)
class ActivateUserOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class ActivateUserUseCase:
    """Activate a previously deactivated user."""

    def __init__(self, uow: UnitOfWork, user_repo: UserRepository) -> None:
        self._uow = uow
        self._user_repo = user_repo

    async def execute(self, input_dto: ActivateUserInput) -> ActivateUserOutput:
        async with self._uow:
            user = await self._user_repo.get_by_id(input_dto.user_id)
            if user is None:
                raise UserNotFoundError(f"User {input_dto.user_id.value} not found")

            user.activate()
            await self._user_repo.save(user)

        return ActivateUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
