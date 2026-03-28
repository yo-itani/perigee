"""CSRF protection via Origin/Referer header verification.

Applied to endpoints that rely on Cookie-based authentication
(e.g. /auth/refresh, /auth/logout, /auth/set-password).
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request


def verify_origin(request: Request, allowed_origins: list[str]) -> None:
    """Verify that the request Origin or Referer matches the allowed origins.

    Raises HTTPException(403) if verification fails.
    """
    origin = request.headers.get("origin")
    if origin and _is_allowed(origin, allowed_origins):
        return

    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
        if _is_allowed(referer_origin, allowed_origins):
            return

    # If neither Origin nor Referer is present, reject the request
    # to prevent CSRF attacks from non-browser clients or hidden forms.
    raise HTTPException(
        status_code=403,
        detail="Origin verification failed",
    )


def _is_allowed(origin: str, allowed_origins: list[str]) -> bool:
    """Check if the given origin is in the allowed list."""
    return origin.rstrip("/") in [o.rstrip("/") for o in allowed_origins]
