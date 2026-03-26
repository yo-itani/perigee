from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.domain.user import User
from shared.domain.value_objects import UserId

_ERROR_DETAIL = "X-User-Id header is missing or invalid"


async def get_current_user_id(
    x_user_id: str | None = Header(default=None),
) -> UserId:
    """Extract and validate UserId from the X-User-Id request header.

    This is a development-only authentication dependency.
    Replace the implementation body with JWT validation (or similar)
    for production use -- router signatures remain unchanged.
    """
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL)

    try:
        return UserId(value=uuid.UUID(x_user_id))
    except ValueError:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL) from None


async def _get_session() -> AsyncGenerator[AsyncSession]:
    """Lazy import wrapper for the shared session factory."""
    from api.dependencies import get_session

    async for s in get_session():
        yield s


async def get_current_user(
    user_id: Annotated[UserId, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(_get_session)],
) -> User:
    """Retrieve the current User from DB and verify it is active."""
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=403, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has admin role. Returns the user if authorized."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
