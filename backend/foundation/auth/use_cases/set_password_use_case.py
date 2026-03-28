"""Use case: set password using an invitation token."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from foundation.auth.invitation_token_repository import InvitationTokenRepository
from foundation.auth.password import hash_password
from foundation.auth.refresh_token_repository import RefreshTokenRepository
from foundation.auth.token_hash import hash_token
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId


class InvalidInvitationTokenError(Exception):
    """Raised when the invitation token is invalid, expired, or already used."""


@dataclass(frozen=True)
class SetPasswordInput:
    token: str
    password: str


@dataclass(frozen=True)
class SetPasswordOutput:
    user_id: str


class SetPasswordUseCase:
    """Set a user's password using an invitation token.

    Also revokes all existing refresh tokens for the user.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        invitation_token_repo: InvitationTokenRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._invitation_token_repo = invitation_token_repo
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, input_dto: SetPasswordInput) -> SetPasswordOutput:
        now = datetime.now(UTC)
        token_h = hash_token(input_dto.token)

        record = await self._invitation_token_repo.find_by_token_hash(token_h)
        if record is None:
            raise InvalidInvitationTokenError("Invitation token not found")

        if record.is_used:
            raise InvalidInvitationTokenError("Invitation token has already been used")

        if record.expires_at < now:
            raise InvalidInvitationTokenError("Invitation token has expired")

        user = await self._user_repo.get_by_id(UserId.from_str(record.user_id))
        if user is None:
            raise InvalidInvitationTokenError("User not found")

        # Set password
        user.set_password_hash(hash_password(input_dto.password))
        await self._user_repo.save(user)

        # Mark token as used
        await self._invitation_token_repo.mark_as_used(record.id)

        # Revoke all existing refresh tokens (password change invalidates sessions)
        await self._refresh_token_repo.revoke_by_user_id(record.user_id)

        return SetPasswordOutput(user_id=record.user_id)
