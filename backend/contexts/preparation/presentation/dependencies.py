"""DI providers for the Preparation context."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_unit_of_work
from contexts.preparation.application.create_schedule_service import (
    CreateScheduleService,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    SqlAlchemyScheduleRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Lazy wrapper around foundation.db.session.get_session.

    Avoids importing the DB engine at module collection time,
    which would fail without the asyncmy driver installed.
    """
    from foundation.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session


def get_schedule_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScheduleRepository:
    """Provide a ScheduleRepository backed by the current DB session."""
    return SqlAlchemyScheduleRepository(session)


def get_create_schedule_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleService:
    """Provide a CreateScheduleService with all dependencies injected."""
    return CreateScheduleService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )
