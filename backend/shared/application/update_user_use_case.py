"""Use case: update a user's name, email, and/or role."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class UpdateUserInput:
    user_id: UserId
    name: str
    email: str
    role: UserRole


@dataclass(frozen=True)
class UpdateUserOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class EmailAlreadyTakenError(Exception):
    """The email address is already used by another user."""


class LastAdminError(Exception):
    """Cannot remove admin role from the last active admin."""


class UpdateUserUseCase:
    """Update a user's name, email, and role (admin only)."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, input_dto: UpdateUserInput) -> UpdateUserOutput:
        user = await self._user_repo.get_by_id(input_dto.user_id)
        if user is None:
            raise UserNotFoundError(f"User {input_dto.user_id.value} not found")

        # Last admin protection: if changing role from admin to member
        if user.role == UserRole.ADMIN and input_dto.role != UserRole.ADMIN:
            active_admin_count = await self._user_repo.count_active_admins()
            if active_admin_count <= 1:
                raise LastAdminError(
                    "Cannot remove admin role from the last active admin"
                )

        # Email uniqueness check
        if user.email != input_dto.email:
            existing = await self._user_repo.get_by_email(input_dto.email)
            if existing is not None and existing.id != user.id:
                raise EmailAlreadyTakenError(
                    f"Email {input_dto.email} is already taken"
                )

        user.update_profile(name=input_dto.name, email=input_dto.email)
        user.change_role(input_dto.role)
        await self._user_repo.save(user)

        return UpdateUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
