"""Tests for CreateInvitationUseCase."""

from __future__ import annotations

import pytest

from foundation.auth.in_memory_invitation_token_repository import (
    InMemoryInvitationTokenRepository,
)
from foundation.auth.use_cases.create_invitation_use_case import (
    CreateInvitationInput,
    CreateInvitationUseCase,
    UserNotFoundError,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


def _make_user(user_id: UserId | None = None) -> User:
    return User(
        id=user_id or UserId.generate(),
        name="Test User",
        email="user@example.com",
        role=UserRole.MEMBER,
    )


class TestCreateInvitation:
    """Tests for CreateInvitationUseCase."""

    async def test_creates_invitation_token(self) -> None:
        """Creates an invitation token for an existing user."""
        user = _make_user()
        user_repo = InMemoryUserRepository(users=[user])
        invitation_repo = InMemoryInvitationTokenRepository()

        use_case = CreateInvitationUseCase(
            user_repo=user_repo,
            invitation_token_repo=invitation_repo,
        )

        output = await use_case.execute(CreateInvitationInput(user_id=user.id))

        assert output.token
        assert output.expires_at is not None
        # Verify a record was stored
        assert len(invitation_repo._records) == 1

    async def test_user_not_found_raises(self) -> None:
        """Raises UserNotFoundError for nonexistent user."""
        user_repo = InMemoryUserRepository()
        invitation_repo = InMemoryInvitationTokenRepository()

        use_case = CreateInvitationUseCase(
            user_repo=user_repo,
            invitation_token_repo=invitation_repo,
        )

        with pytest.raises(UserNotFoundError):
            await use_case.execute(CreateInvitationInput(user_id=UserId.generate()))
