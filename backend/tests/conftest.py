"""Root conftest: environment defaults and shared DB fixtures.

This module provides:
- Default env vars so Settings() can be instantiated without .env
- Shared test DB engine, session, and session_factory fixtures
  (consolidated from per-context infrastructure conftest files)
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Provide a default JWT secret for tests so that Settings() can be
# instantiated even when the real .env is absent.  Individual tests
# may override via monkeypatch or unittest.mock.patch.
os.environ.setdefault(
    "PERIGEE_JWT_SECRET_KEY",
    "test-secret-key-for-unit-tests-32chars!",
)


def _test_database_url() -> str:
    """Build a URL pointing to the perigee_test database."""
    from foundation.config.settings import settings

    return (
        f"mysql+asyncmy://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/perigee_test"
    )


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create a test engine that connects to perigee_test.

    Shared across all integration test modules -- previously each
    context's infrastructure conftest duplicated this fixture.
    """
    import foundation.db.models  # noqa: F401 -- register all ORM models
    from foundation.db.base import Base

    engine = create_async_engine(
        _test_database_url(),
        echo=False,
        pool_pre_ping=True,
        connect_args={"init_command": "SET time_zone='+00:00'"},
    )
    # Create all tables at the start of the test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables at the end of the test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    """Provide a session that rolls back uncommitted changes after each test.

    Each test is responsible for its own data setup.
    """
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as s:
        yield s
        # Roll back any uncommitted changes after each test
        await s.rollback()


@pytest.fixture
def session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Provide a session factory for tests that need multiple sessions."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
