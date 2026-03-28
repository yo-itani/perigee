"""Root conftest: ensure required env vars are available for all tests."""

import os

# Provide a default JWT secret for tests so that Settings() can be
# instantiated even when the real .env is absent.  Individual tests
# may override via monkeypatch or unittest.mock.patch.
os.environ.setdefault(
    "PERIGEE_JWT_SECRET_KEY",
    "test-secret-key-for-unit-tests-32chars!",
)
