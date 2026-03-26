from __future__ import annotations

import uuid

from fastapi import Header, HTTPException

from shared.domain.value_objects import UserId

_ERROR_DETAIL = "X-User-Id header is missing or invalid"


def parse_user_id_header(
    x_user_id: str | None = Header(default=None),
) -> UserId:
    """Parse and validate the X-User-Id header value.

    This is a development-only header parser.
    Replace with JWT token extraction for production use.
    """
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=_ERROR_DETAIL)

    try:
        return UserId(value=uuid.UUID(x_user_id))
    except ValueError:
        raise HTTPException(
            status_code=401, detail=_ERROR_DETAIL,
        ) from None
