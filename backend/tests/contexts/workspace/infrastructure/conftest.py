from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import foundation.db.models  # noqa: F401
from foundation.config.settings import settings
from foundation.db.base import Base


def _test_database_url() -> str:
    """Build a URL pointing to the perigee_test database."""
    return (
        f"mysql+asyncmy://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/perigee_test"
    )


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create a test engine that connects to perigee_test."""
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
    """Provide a transactional session that rolls back after each test."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        # Roll back any uncommitted changes after each test
        await session.rollback()


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
