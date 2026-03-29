"""Use case: deactivate a user."""

from __future__ import annotations

from dataclasses import dataclass

from foundation.application.unit_of_work import UnitOfWork
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class DeactivateUserInput:
    user_id: UserId


@dataclass(frozen=True)
class DeactivateUserOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class LastAdminError(Exception):
    """Cannot deactivate the last active admin."""


class DeactivateUserUseCase:
    """Deactivate a user (soft delete)."""

    def __init__(self, uow: UnitOfWork, user_repo: UserRepository) -> None:
        self._uow = uow
        self._user_repo = user_repo

    async def execute(self, input_dto: DeactivateUserInput) -> DeactivateUserOutput:
        async with self._uow:
            user = await self._user_repo.get_by_id(input_dto.user_id)
            if user is None:
                raise UserNotFoundError(f"User {input_dto.user_id.value} not found")

            # Last admin protection
            if user.role == UserRole.ADMIN:
                active_admin_count = await self._user_repo.count_active_admins()
                if active_admin_count <= 1:
                    raise LastAdminError("Cannot deactivate the last active admin")

            user.deactivate()
            await self._user_repo.save(user)
            await self._uow.commit()

        return DeactivateUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
