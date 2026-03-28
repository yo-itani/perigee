"""Utilities for hashing opaque tokens (refresh / invitation tokens).

Uses SHA-256 for fast, non-reversible hashing of random tokens.
Unlike passwords, these tokens are high-entropy random strings,
so bcrypt is unnecessary.
"""

import hashlib
import secrets


def generate_token() -> str:
    """Generate a cryptographically secure random token (URL-safe)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
