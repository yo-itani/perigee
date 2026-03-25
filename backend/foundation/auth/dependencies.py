from __future__ import annotations

import uuid

from fastapi import Header, HTTPException

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
