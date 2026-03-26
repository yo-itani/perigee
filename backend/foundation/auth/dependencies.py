from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from shared.domain.user import User
from shared.domain.value_objects import UserId

_ERROR_DETAIL = "X-User-Id header is missing or invalid"


def _parse_user_id_header(
    x_user_id: str | None = Header(default=None),
) -> UserId:
    """Parse and validate the X-User-Id header value."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL)

    try:
        return UserId(value=uuid.UUID(x_user_id))
    except ValueError:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL) from None


async def get_current_user_id(
    parsed_id: Annotated[UserId, Depends(_parse_user_id_header)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserId:
    """Extract and verify UserId from X-User-Id header.

    This is a development-only authentication dependency.
    Replace the implementation body with JWT validation (or similar)
    for production use -- router signatures remain unchanged.
    """
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(parsed_id)
    if user is None:
        raise HTTPException(status_code=403, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    return parsed_id


async def get_current_user(
    user_id: Annotated[UserId, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Retrieve the current User from DB.

    The user is already verified to exist and be active by
    ``get_current_user_id``, so this only fetches the full object.
    """
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    # Should not happen since get_current_user_id already verified
    if user is None:  # pragma: no cover
        raise HTTPException(status_code=403, detail="User not found")
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has admin role. Returns the user if authorized."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
