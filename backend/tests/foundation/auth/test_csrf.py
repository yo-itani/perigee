"""Tests for CSRF Origin/Referer verification."""

import pytest
from fastapi import HTTPException

from foundation.auth.csrf import verify_origin

_ALLOWED = ["http://localhost:5173", "http://127.0.0.1:5173"]


class _FakeRequest:
    """Minimal request mock for testing."""

    def __init__(
        self,
        origin: str | None = None,
        referer: str | None = None,
    ) -> None:
        self.headers: dict[str, str] = {}
        if origin is not None:
            self.headers["origin"] = origin
        if referer is not None:
            self.headers["referer"] = referer


def test_valid_origin_passes() -> None:
    req = _FakeRequest(origin="http://localhost:5173")
    verify_origin(req, _ALLOWED)  # type: ignore[arg-type]


def test_valid_referer_passes() -> None:
    req = _FakeRequest(
        referer="http://localhost:5173/auth/set-password"
    )
    verify_origin(req, _ALLOWED)  # type: ignore[arg-type]


def test_no_origin_no_referer_raises() -> None:
    req = _FakeRequest()
    with pytest.raises(HTTPException) as exc_info:
        verify_origin(req, _ALLOWED)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403


def test_wrong_origin_raises() -> None:
    req = _FakeRequest(origin="http://evil.com")
    with pytest.raises(HTTPException) as exc_info:
        verify_origin(req, _ALLOWED)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403


def test_trailing_slash_is_normalized() -> None:
    req = _FakeRequest(origin="http://localhost:5173/")
    verify_origin(req, _ALLOWED)  # type: ignore[arg-type]
