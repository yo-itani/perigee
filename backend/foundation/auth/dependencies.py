"""Authentication dependencies for FastAPI.

Extracts and validates JWT access tokens from the Authorization header.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from foundation.auth.jwt_token import TokenError, decode_access_token
from shared.domain.value_objects import UserId

_bearer_scheme = HTTPBearer(auto_error=False)

_AUTH_ERROR_DETAIL = "Not authenticated"


async def parse_user_id_from_jwt(
    request: Request,
) -> UserId:
    """Extract and validate the JWT access token from the Authorization header.

    Returns the authenticated UserId.
    """
    from foundation.config.settings import settings

    credentials: HTTPAuthorizationCredentials | None = await _bearer_scheme(request)
    if credentials is None:
        raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL)

    try:
        user_id_str = decode_access_token(
            credentials.credentials, settings.jwt_secret_key
        )
    except TokenError:
        raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL) from None

    try:
        return UserId(value=uuid.UUID(user_id_str))
    except ValueError:
        raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL) from None
