"""Use case: authenticate a user with email and password."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from foundation.auth.jwt_token import create_access_token
from foundation.auth.login_attempt_repository import (
    LoginAttemptRecord,
    LoginAttemptRepository,
)
from foundation.auth.password import verify_password
from foundation.auth.refresh_token_repository import (
    RefreshTokenRecord,
    RefreshTokenRepository,
)
from foundation.auth.token_hash import generate_token, hash_token
from shared.domain.user_repository import UserRepository

_LOCKOUT_THRESHOLD = 10
_LOCKOUT_MINUTES = 15


class InvalidCredentialsError(Exception):
    """Raised when email or password is incorrect."""


class AccountLockedError(Exception):
    """Raised when the account is temporarily locked due to too many failed attempts."""


class AccountDeactivatedError(Exception):
    """Raised when the account is deactivated."""


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    ip_address: str


@dataclass(frozen=True)
class LoginOutput:
    access_token: str
    refresh_token: str  # raw token (to be set in cookie)
    user_id: str


class LoginUseCase:
    """Authenticate a user and issue JWT + refresh token."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        login_attempt_repo: LoginAttemptRepository,
        jwt_secret_key: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._login_attempt_repo = login_attempt_repo
        self._jwt_secret_key = jwt_secret_key
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    async def execute(self, input_dto: LoginInput) -> LoginOutput:
        now = datetime.now(UTC)

        # Check lockout
        lockout_since = now - timedelta(minutes=_LOCKOUT_MINUTES)
        recent_failures = await self._login_attempt_repo.count_recent_failures(
            input_dto.email, lockout_since
        )
        if recent_failures >= _LOCKOUT_THRESHOLD:
            raise AccountLockedError(
                "Account is temporarily locked. "
                f"Try again after {_LOCKOUT_MINUTES} minutes."
            )

        # Find user
        user = await self._user_repo.get_by_email(input_dto.email)

        if user is None or not user.has_password:
            # Record failed attempt
            await self._record_attempt(
                input_dto.email, input_dto.ip_address, now, is_success=False
            )
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            await self._record_attempt(
                input_dto.email, input_dto.ip_address, now, is_success=False
            )
            raise AccountDeactivatedError("Account is deactivated")

        if not verify_password(input_dto.password, user.password_hash):  # type: ignore[arg-type]
            await self._record_attempt(
                input_dto.email, input_dto.ip_address, now, is_success=False
            )
            raise InvalidCredentialsError("Invalid email or password")

        # Record successful attempt
        await self._record_attempt(
            input_dto.email, input_dto.ip_address, now, is_success=True
        )

        # Create access token
        user_id_str = str(user.id.value)
        access_token = create_access_token(
            user_id=user_id_str,
            secret_key=self._jwt_secret_key,
            expire_minutes=self._access_token_expire_minutes,
        )

        # Create refresh token
        raw_refresh_token = generate_token()
        token_family_id = str(uuid.uuid4())
        refresh_record = RefreshTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=hash_token(raw_refresh_token),
            user_id=user_id_str,
            token_family_id=token_family_id,
            expires_at=now + timedelta(days=self._refresh_token_expire_days),
            is_revoked=False,
            created_at=now,
        )
        await self._refresh_token_repo.save(refresh_record)

        return LoginOutput(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            user_id=user_id_str,
        )

    async def _record_attempt(
        self, email: str, ip_address: str, now: datetime, *, is_success: bool
    ) -> None:
        record = LoginAttemptRecord(
            id=str(uuid.uuid4()),
            email=email,
            ip_address=ip_address,
            attempted_at=now,
            is_success=is_success,
        )
        await self._login_attempt_repo.save(record)
