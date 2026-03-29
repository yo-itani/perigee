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
from sqlalchemy.pool import NullPool

# Provide defaults for tests so that Settings() can be instantiated
# even when the real .env is absent.  Individual tests may override
# via monkeypatch or unittest.mock.patch.
os.environ.setdefault(
    "PERIGEE_JWT_SECRET_KEY",
    "test-secret-key-for-unit-tests-32chars!",
)
os.environ.setdefault("PERIGEE_DB_HOST", "localhost")
os.environ.setdefault("PERIGEE_DB_USER", "perigee_test")
os.environ.setdefault("PERIGEE_DB_PASSWORD", "perigee_test")
os.environ.setdefault("PERIGEE_DB_NAME", "perigee_test")


def _test_database_url() -> str:
    """Build a URL pointing to the perigee_test database."""
    from foundation.config.settings import settings

    return (
        f"mysql+asyncmy://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/perigee_test"
    )


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    """Create a test engine that connects to perigee_test.

    Sync fixture so it is not bound to any specific event loop.
    NullPool avoids cross-loop connection reuse.
    Tables are created/dropped via temporary loops at session boundaries.
    """
    import asyncio

    import foundation.db.models  # noqa: F401 -- register all ORM models
    from foundation.db.base import Base

    url = _test_database_url()

    engine = create_async_engine(
        url,
        echo=False,
        poolclass=NullPool,
        connect_args={"init_command": "SET time_zone='+00:00'"},
    )

    async def _create_tables() -> None:
        setup_engine = create_async_engine(url, poolclass=NullPool)
        async with setup_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await setup_engine.dispose()

    async def _drop_tables() -> None:
        teardown_engine = create_async_engine(url, poolclass=NullPool)
        async with teardown_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await teardown_engine.dispose()
        await engine.dispose()

    asyncio.run(_create_tables())
    yield engine
    asyncio.run(_drop_tables())


@pytest.fixture(autouse=True)
def _ensure_tables(request: pytest.FixtureRequest) -> None:
    """Ensure DB tables exist for every integration test.

    Presentation tests hit the DB via ``app`` (not via the ``session``
    fixture), so they also need tables created by ``test_engine``.
    Unit tests (no ``integration`` marker) skip DB setup entirely.
    """
    if request.node.get_closest_marker("integration") is None:
        return
    request.getfixturevalue("test_engine")


@pytest.fixture(autouse=True)
def _dispose_app_engine(request: pytest.FixtureRequest) -> None:
    """Dispose the application's DB engine pool after each integration test.

    pytest-asyncio creates a new event loop per test function. The app-level
    engine (foundation.db.session.engine) uses QueuePool, so connections
    created on a previous loop become stale. Disposing the sync engine
    after each test forces fresh connections on the next loop.
    """
    yield
    if request.node.get_closest_marker("integration") is None:
        return
    import sys

    mod = sys.modules.get("foundation.db.session")
    if mod is None:
        return
    try:
        mod.engine.sync_engine.dispose()
    except Exception:
        pass


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
