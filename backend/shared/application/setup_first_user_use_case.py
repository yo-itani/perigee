"""Use case: set up the first user (admin) when the system has no users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from foundation.application.unit_of_work import UnitOfWork
from shared.domain.system_settings_repository import SystemSettingsRepository
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
    """Raised when setup is attempted but setup is already complete."""


class SetupFirstUserUseCase:
    """Create the first admin user. Only allowed when setup is not yet complete.

    Uses ``SystemSettingsRepository.get_for_update()`` (SELECT ... FOR UPDATE)
    on the singleton system_settings row to prevent concurrent requests from
    both passing the "not yet set up" check.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        system_settings_repo: SystemSettingsRepository,
        uow: UnitOfWork,
    ) -> None:
        self._user_repo = user_repo
        self._system_settings_repo = system_settings_repo
        self._uow = uow

    async def execute(self, input_dto: SetupFirstUserInput) -> SetupFirstUserOutput:
        async with self._uow:
            settings = await self._system_settings_repo.get_for_update()
            if settings.is_setup_complete:
                raise SetupAlreadyCompleteError("Setup is already complete.")

            user = User(
                id=UserId.generate(),
                name=input_dto.name,
                email=input_dto.email,
                role=UserRole.ADMIN,
            )
            await self._user_repo.save(user)

            now = datetime.now(UTC)
            settings.mark_setup_complete(now)
            await self._system_settings_repo.save(settings)

            await self._uow.commit()

        return SetupFirstUserOutput(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
