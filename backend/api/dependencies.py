"""Shared DI providers for FastAPI Depends chains."""

from __future__ import annotations

from fastapi import Request

from foundation.application.unit_of_work import UnitOfWork
from foundation.db.session import async_session_factory
from foundation.domain.event_dispatcher import EventDispatcher
from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_unit_of_work() -> UnitOfWork:
    """Provide a new UnitOfWork backed by SQLAlchemy."""
    return SqlAlchemyUnitOfWork(async_session_factory)


def get_event_dispatcher(request: Request) -> EventDispatcher:
    """Return the app-scope singleton EventDispatcher from app.state."""
    dispatcher: EventDispatcher = request.app.state.event_dispatcher
    return dispatcher
