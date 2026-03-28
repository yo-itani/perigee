"""JWT access token creation and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

_ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when a JWT token is invalid or expired."""


def create_access_token(
    user_id: str,
    secret_key: str,
    expire_minutes: int,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> str:
    """Decode and validate a JWT access token. Returns the user_id (sub)."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Access token has expired") from None
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid access token: {exc}") from None

    if payload.get("type") != "access":
        raise TokenError("Invalid token type")

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise TokenError("Token missing subject")

    return sub
