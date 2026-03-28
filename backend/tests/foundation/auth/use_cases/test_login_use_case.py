"""Tests for LoginUseCase."""

from __future__ import annotations

import pytest

from foundation.auth.in_memory_login_attempt_repository import (
    InMemoryLoginAttemptRepository,
)
from foundation.auth.in_memory_refresh_token_repository import (
    InMemoryRefreshTokenRepository,
)
from foundation.auth.password import hash_password
from foundation.auth.use_cases.login_use_case import (
    AccountDeactivatedError,
    AccountLockedError,
    InvalidCredentialsError,
    LoginInput,
    LoginUseCase,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import (
    InMemoryUserRepository,
)

_SECRET = "test-secret-key-for-unit-tests-32chars!"
_ACCESS_EXPIRE = 30
_REFRESH_EXPIRE = 7
_IP = "127.0.0.1"


def _login(
    email: str = "user@example.com",
    password: str = "correct-password",
) -> LoginInput:
    return LoginInput(email=email, password=password, ip_address=_IP)


def _make_user(
    *,
    email: str = "user@example.com",
    password: str = "correct-password",
    is_active: bool = True,
    role: UserRole = UserRole.MEMBER,
) -> User:
    return User(
        id=UserId.generate(),
        name="Test User",
        email=email,
        role=role,
        is_active=is_active,
        password_hash=hash_password(password),
    )


def _make_use_case(
    user_repo: InMemoryUserRepository,
    refresh_repo: InMemoryRefreshTokenRepository | None = None,
    login_attempt_repo: InMemoryLoginAttemptRepository | None = None,
) -> LoginUseCase:
    return LoginUseCase(
        user_repo=user_repo,
        refresh_token_repo=(refresh_repo or InMemoryRefreshTokenRepository()),
        login_attempt_repo=(login_attempt_repo or InMemoryLoginAttemptRepository()),
        jwt_secret_key=_SECRET,
        access_token_expire_minutes=_ACCESS_EXPIRE,
        refresh_token_expire_days=_REFRESH_EXPIRE,
    )


class TestLoginSuccess:
    """Tests for successful login."""

    async def test_returns_tokens(self) -> None:
        """Successful login returns access and refresh tokens."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        use_case = _make_use_case(repo)

        output = await use_case.execute(_login())

        assert output.access_token
        assert output.refresh_token
        assert output.user_id == str(user.id.value)

    async def test_records_successful_attempt(self) -> None:
        """Successful login records a success attempt."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        attempts = InMemoryLoginAttemptRepository()
        use_case = _make_use_case(repo, login_attempt_repo=attempts)

        await use_case.execute(_login())

        assert len(attempts._records) == 1
        assert attempts._records[0].is_success is True

    async def test_stores_refresh_token(self) -> None:
        """Successful login stores a refresh token record."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        refresh_repo = InMemoryRefreshTokenRepository()
        use_case = _make_use_case(repo, refresh_repo=refresh_repo)

        await use_case.execute(_login())

        assert len(refresh_repo._records) == 1


class TestLoginFailure:
    """Tests for login failures."""

    async def test_wrong_password_raises(self) -> None:
        """Wrong password raises InvalidCredentialsError."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        use_case = _make_use_case(repo)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(_login(password="wrong-password"))

    async def test_nonexistent_user_raises(self) -> None:
        """Nonexistent email raises InvalidCredentialsError."""
        repo = InMemoryUserRepository()
        use_case = _make_use_case(repo)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(_login(email="noone@example.com", password="any"))

    async def test_user_without_password_raises(self) -> None:
        """User with no password hash raises InvalidCredentialsError."""
        user = User(
            id=UserId.generate(),
            name="No Password",
            email="nopass@example.com",
            role=UserRole.MEMBER,
        )
        repo = InMemoryUserRepository(users=[user])
        use_case = _make_use_case(repo)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(_login(email="nopass@example.com", password="any"))

    async def test_deactivated_user_raises(self) -> None:
        """Deactivated user raises AccountDeactivatedError."""
        user = _make_user(is_active=False)
        repo = InMemoryUserRepository(users=[user])
        use_case = _make_use_case(repo)

        with pytest.raises(AccountDeactivatedError):
            await use_case.execute(_login())

    async def test_records_failed_attempt(self) -> None:
        """Failed login records a failure attempt."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        attempts = InMemoryLoginAttemptRepository()
        use_case = _make_use_case(repo, login_attempt_repo=attempts)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(_login(password="wrong"))

        assert len(attempts._records) == 1
        assert attempts._records[0].is_success is False


class TestAccountLockout:
    """Tests for account lockout after too many failed attempts."""

    async def test_lockout_after_10_failures(self) -> None:
        """Account is locked after 10 consecutive failures."""
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])
        attempts = InMemoryLoginAttemptRepository()
        use_case = _make_use_case(repo, login_attempt_repo=attempts)

        # Fail 10 times
        for _ in range(10):
            with pytest.raises(InvalidCredentialsError):
                await use_case.execute(_login(password="wrong"))

        # 11th attempt should be locked even with correct password
        with pytest.raises(AccountLockedError):
            await use_case.execute(_login())
