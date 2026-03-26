from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from shared.domain.user import User
from shared.domain.value_objects import UserId

_ERROR_DETAIL = "X-User-Id header is missing or invalid"
_REQUEST_USER_KEY = "_current_user"


def _parse_user_id_header(
    x_user_id: str | None = Header(default=None),
) -> UserId:
    """Parse and validate the X-User-Id header value."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL)

    try:
        return UserId(value=uuid.UUID(x_user_id))
    except ValueError:
        raise HTTPException(
            status_code=401, detail=_ERROR_DETAIL,
        ) from None


async def get_current_user_id(
    request: Request,
    parsed_id: Annotated[UserId, Depends(_parse_user_id_header)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserId:
    """Extract and verify UserId from X-User-Id header.

    This is a development-only authentication dependency.
    Replace the implementation body with JWT validation (or
    similar) for production use -- router signatures unchanged.
    """
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(parsed_id)
    if user is None:
        raise HTTPException(
            status_code=403, detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is deactivated",
        )
    # Cache for get_current_user to avoid duplicate query
    request.state._current_user = user  # noqa: SLF001
    return parsed_id


async def get_current_user(
    request: Request,
    user_id: Annotated[UserId, Depends(get_current_user_id)],
) -> User:
    """Return the current User, cached by get_current_user_id."""
    return request.state._current_user  # noqa: SLF001


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Admin access required",
        )
    return current_user
