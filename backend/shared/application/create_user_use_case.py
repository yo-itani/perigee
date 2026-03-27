"""Use case: create a new user."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class CreateUserInput:
    name: str
    email: str
    role: UserRole


@dataclass(frozen=True)
class CreateUserOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class EmailAlreadyTakenError(Exception):
    """The email address is already used by another user."""


class CreateUserUseCase:
    """Create a new user in the system."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, input_dto: CreateUserInput) -> CreateUserOutput:
        existing = await self._user_repo.get_by_email(input_dto.email)
        if existing is not None:
            raise EmailAlreadyTakenError(f"Email {input_dto.email} is already taken")

        user = User(
            id=UserId.generate(),
            name=input_dto.name,
            email=input_dto.email,
            role=input_dto.role,
        )
        await self._user_repo.save(user)

        return CreateUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
