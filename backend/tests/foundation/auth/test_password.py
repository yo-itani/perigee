"""Tests for password hashing and verification."""

from foundation.auth.password import hash_password, verify_password


def test_hash_and_verify_correct_password() -> None:
    plain = "my-secure-password"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)


def test_verify_wrong_password_returns_false() -> None:
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_hash_produces_different_salts() -> None:
    plain = "same-password"
    h1 = hash_password(plain)
    h2 = hash_password(plain)
    assert h1 != h2  # Different salts
    assert verify_password(plain, h1)
    assert verify_password(plain, h2)
