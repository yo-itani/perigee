"""Use case: generate an invitation link for a user to set their password."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from foundation.application.unit_of_work import UnitOfWork
from foundation.auth.invitation_token_repository import (
    InvitationTokenRecord,
    InvitationTokenRepository,
)
from foundation.auth.token_hash import generate_token, hash_token
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId

_INVITATION_EXPIRE_HOURS = 72


class UserNotFoundError(Exception):
    """Raised when the target user does not exist."""


@dataclass(frozen=True)
class CreateInvitationInput:
    user_id: UserId


@dataclass(frozen=True)
class CreateInvitationOutput:
    token: str  # raw token to include in the invitation URL
    expires_at: datetime


class CreateInvitationUseCase:
    """Generate an invitation token for a user."""

    def __init__(
        self,
        uow: UnitOfWork,
        user_repo: UserRepository,
        invitation_token_repo: InvitationTokenRepository,
    ) -> None:
        self._uow = uow
        self._user_repo = user_repo
        self._invitation_token_repo = invitation_token_repo

    async def execute(self, input_dto: CreateInvitationInput) -> CreateInvitationOutput:
        async with self._uow:
            user = await self._user_repo.get_by_id(input_dto.user_id)
            if user is None:
                raise UserNotFoundError("User not found")

            now = datetime.now(UTC)
            raw_token = generate_token()
            expires_at = now + timedelta(hours=_INVITATION_EXPIRE_HOURS)

            record = InvitationTokenRecord(
                id=str(uuid.uuid4()),
                token_hash=hash_token(raw_token),
                user_id=str(user.id.value),
                expires_at=expires_at,
                is_used=False,
                created_at=now,
            )
            await self._invitation_token_repo.save(record)

        return CreateInvitationOutput(token=raw_token, expires_at=expires_at)
