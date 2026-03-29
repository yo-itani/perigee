from __future__ import annotations

from dataclasses import dataclass

from foundation.application.unit_of_work import UnitOfWork
from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class UpdateMyProfileInput:
    name: str
    email: str


@dataclass(frozen=True)
class UpdateMyProfileOutput:
    id: UserId
    name: str
    email: str


class UserNotFoundError(Exception):
    """The requested user does not exist."""


class EmailAlreadyTakenError(Exception):
    """The email address is already used by another user."""


class UpdateMyProfileUseCase:
    """Update the current user's name and email."""

    def __init__(
        self,
        user_repo: UserRepository,
        uow: UnitOfWork,
    ) -> None:
        self._user_repo = user_repo
        self._uow = uow

    async def execute(
        self, input_dto: UpdateMyProfileInput, current_user: User
    ) -> UpdateMyProfileOutput:
        async with self._uow:
            # Check email uniqueness if changed
            if current_user.email != input_dto.email:
                existing = await self._user_repo.get_by_email(input_dto.email)
                if existing is not None and existing.id != current_user.id:
                    raise EmailAlreadyTakenError(
                        f"Email {input_dto.email} is already taken"
                    )

            current_user.update_profile(name=input_dto.name, email=input_dto.email)
            await self._user_repo.save(current_user)
            await self._uow.commit()

        return UpdateMyProfileOutput(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
        )
