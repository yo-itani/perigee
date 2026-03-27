"""Use case: set up the first user (admin) when the system has no users."""

from __future__ import annotations

from dataclasses import dataclass

from foundation.application.unit_of_work import UnitOfWork
from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


@dataclass(frozen=True)
class SetupFirstUserInput:
    name: str
    email: str


@dataclass(frozen=True)
class SetupFirstUserOutput:
    id: UserId
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


class SetupAlreadyCompleteError(Exception):
    """Raised when setup is attempted but users already exist."""


class SetupFirstUserUseCase:
    """Create the first admin user. Only allowed when no users exist.

    Uses ``count_all_for_update()`` (SELECT ... FOR UPDATE) inside a
    transaction to prevent concurrent requests from both passing the
    "no users" check.
    """

    def __init__(self, user_repo: UserRepository, uow: UnitOfWork) -> None:
        self._user_repo = user_repo
        self._uow = uow

    async def execute(self, input_dto: SetupFirstUserInput) -> SetupFirstUserOutput:
        async with self._uow:
            count = await self._user_repo.count_all_for_update()
            if count > 0:
                raise SetupAlreadyCompleteError(
                    "Setup is already complete. Users already exist."
                )

            user = User(
                id=UserId.generate(),
                name=input_dto.name,
                email=input_dto.email,
                role=UserRole.ADMIN,
            )
            await self._user_repo.save(user)
            await self._uow.commit()

        return SetupFirstUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
