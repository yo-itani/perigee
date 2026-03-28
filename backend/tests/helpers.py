"""Shared test helper functions.

Provides:
- Test user creation helpers (DB row insertion)
- JWT token generation for authenticated test requests
- httpx AsyncClient builder with ASGITransport
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable


def _get_test_secret() -> str:
    """Return the JWT secret key used by the application under test.

    Reads from settings so that the signing key always matches the key
    the app uses for verification, even when PERIGEE_JWT_SECRET_KEY is
    overridden via environment variables.
    """
    from foundation.config.settings import settings

    return settings.jwt_secret_key


# ---------------------------------------------------------------------------
# Test user helpers (DB)
# ---------------------------------------------------------------------------


def make_test_user_table(
    id: str,
    name: str = "Test User",
    email: str | None = None,
    role: str = "member",
    is_active: bool = True,
    slack_user_id: str | None = None,
) -> UserTable:
    """Create a UserTable row for testing.

    If email is not provided, generates one from the id.
    """
    return UserTable(
        id=id,
        name=name,
        email=email or f"{id}@test.local",
        role=role,
        is_active=is_active,
        slack_user_id=slack_user_id,
    )


async def create_test_user(
    session: AsyncSession,
    user_id: UserId | None = None,
    name: str = "Test User",
    email: str | None = None,
    role: str = "member",
    is_active: bool = True,
) -> UserId:
    """Insert a user row and return its UserId (needed for FK constraints)."""
    uid = user_id or UserId.generate()
    row = make_test_user_table(
        id=str(uid.value),
        name=name,
        email=email,
        role=role,
        is_active=is_active,
    )
    session.add(row)
    await session.flush()
    return uid


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------


def create_test_access_token(
    user_id: str | UserId,
    *,
    expire_minutes: int = 30,
    secret_key: str | None = None,
) -> str:
    """Create a valid JWT access token for test requests.

    Uses the same signing logic as the production code so that the real
    auth middleware can validate the token without any DI overrides.
    ``secret_key`` defaults to ``settings.jwt_secret_key`` so it always
    matches the key used by the app for verification.
    """
    from foundation.auth.jwt_token import create_access_token

    key = secret_key if secret_key is not None else _get_test_secret()
    uid_str = str(user_id.value) if isinstance(user_id, UserId) else user_id
    return create_access_token(uid_str, key, expire_minutes)


def auth_headers(
    user_id: str | UserId,
    *,
    expire_minutes: int = 30,
    secret_key: str | None = None,
) -> dict[str, str]:
    """Return an Authorization header dict with a valid Bearer token.

    Usage::

        headers = auth_headers(user_id)
        response = await client.get("/some-endpoint", headers=headers)
    """
    token = create_test_access_token(
        user_id, expire_minutes=expire_minutes, secret_key=secret_key
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# httpx AsyncClient helpers
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://test"


@asynccontextmanager
async def create_async_client(
    app: object,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    headers: dict[str, str] | None = None,
) -> AsyncGenerator[AsyncClient]:
    """Create an httpx AsyncClient wired to a FastAPI app via ASGITransport.

    Usage::

        async with create_async_client(app) as client:
            resp = await client.get("/health")

        # With auth:
        hdrs = auth_headers(user_id)
        async with create_async_client(app, headers=hdrs) as client:
            resp = await client.get("/protected")
    """
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(
        transport=transport, base_url=base_url, headers=headers
    ) as client:
        yield client


@asynccontextmanager
async def create_authenticated_client(
    app: object,
    user_id: str | UserId,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    secret_key: str | None = None,
) -> AsyncGenerator[AsyncClient]:
    """Create an httpx AsyncClient with JWT auth headers pre-configured.

    Combines create_async_client and auth_headers into a single helper::

        async with create_authenticated_client(app, user_id) as client:
            resp = await client.get("/protected")
    """
    headers = auth_headers(user_id, secret_key=secret_key)
    async with create_async_client(app, base_url=base_url, headers=headers) as client:
        yield client
