"""DI providers for the Record context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordUseCase,
)
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher


def get_record_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecordRepository:
    """Provide a RecordRepository backed by the current DB session."""
    return SqlAlchemyRecordRepository(session)


def get_create_post_hoc_record_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreatePostHocRecordUseCase:
    """Provide a CreatePostHocRecordUseCase with all dependencies injected."""
    return CreatePostHocRecordUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )
