"""Tests for opaque token generation and hashing."""

from foundation.auth.token_hash import generate_token, hash_token


def test_generate_token_returns_nonempty_string() -> None:
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_token_is_unique() -> None:
    t1 = generate_token()
    t2 = generate_token()
    assert t1 != t2


def test_hash_token_is_deterministic() -> None:
    token = "my-token-value"
    h1 = hash_token(token)
    h2 = hash_token(token)
    assert h1 == h2


def test_different_tokens_produce_different_hashes() -> None:
    h1 = hash_token("token-a")
    h2 = hash_token("token-b")
    assert h1 != h2
