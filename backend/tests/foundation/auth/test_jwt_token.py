"""Tests for JWT token creation and verification."""

import time

import pytest

from foundation.auth.jwt_token import (
    TokenError,
    create_access_token,
    decode_access_token,
)

_SECRET = "test-secret-long-enough-for-hs256!"


def test_create_and_decode_access_token() -> None:
    user_id = "abc-123"
    token = create_access_token(
        user_id=user_id, secret_key=_SECRET, expire_minutes=30
    )
    result = decode_access_token(token, _SECRET)
    assert result == user_id


def test_decode_with_wrong_secret_raises() -> None:
    token = create_access_token(
        user_id="user-1", secret_key=_SECRET, expire_minutes=30
    )
    with pytest.raises(TokenError, match="Invalid access token"):
        decode_access_token(token, "wrong-secret-long-enough-for-hs256!")


def test_expired_token_raises() -> None:
    token = create_access_token(
        user_id="user-1", secret_key=_SECRET, expire_minutes=0
    )
    time.sleep(1)
    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token, _SECRET)
