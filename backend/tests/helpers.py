"""Shared test helper functions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable


def make_test_user_table(
    id: str,
    name: str = "Test User",
    email: str | None = None,
    role: str = "member",
    is_active: bool = True,
    slack_user_id: str | None = None,
) -> UserTable:
    """Create a UserTable row for testing.

    If email is not provided, generates one from the id.
    """
    return UserTable(
        id=id,
        name=name,
        email=email or f"{id}@test.local",
        role=role,
        is_active=is_active,
        slack_user_id=slack_user_id,
    )


async def create_test_user(
    session: AsyncSession,
    user_id: UserId | None = None,
    name: str = "Test User",
    email: str | None = None,
    role: str = "member",
    is_active: bool = True,
) -> UserId:
    """Insert a user row and return its UserId (needed for FK constraints)."""
    uid = user_id or UserId.generate()
    row = make_test_user_table(
        id=str(uid.value),
        name=name,
        email=email,
        role=role,
        is_active=is_active,
    )
    session.add(row)
    await session.flush()
    return uid
