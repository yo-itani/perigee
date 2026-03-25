"""Shared DI providers for FastAPI Depends chains."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a DB session scoped to a single request.

    Uses a lazy import to avoid importing the DB engine at module
    collection time, which would fail without the asyncmy driver.

    All DI providers that need a session should depend on this single
    callable so that repositories and the UoW share the same session.
    """
    from foundation.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session


def get_unit_of_work(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWork:
    """Provide a UnitOfWork backed by the shared request-scoped session."""
    from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

    return SqlAlchemyUnitOfWork(session)


def get_event_dispatcher(request: Request) -> EventDispatcher:
    """Return the app-scope singleton EventDispatcher from app.state."""
    dispatcher: EventDispatcher = request.app.state.event_dispatcher
    return dispatcher
