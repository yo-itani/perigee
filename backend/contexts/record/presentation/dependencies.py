"""DI providers for the Record context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    SqlAlchemyScheduleRepository,
)
from contexts.record.application.add_action_item import AddActionItemUseCase
from contexts.record.application.confirm_agenda import ConfirmAgendaUseCase
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordUseCase,
)
from contexts.record.application.create_record_from_schedule import (
    CreateRecordFromScheduleUseCase,
)
from contexts.record.application.delete_action_item import DeleteActionItemUseCase
from contexts.record.application.save_draft import SaveDraftUseCase
from contexts.record.application.update_memo import UpdateMemoUseCase
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.infrastructure.sqlalchemy_action_item_repository import (
    SqlAlchemyActionItemRepository,
)
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher

# ---------------------------------------------------------------------------
# Repository providers
# ---------------------------------------------------------------------------


def get_record_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecordRepository:
    """Provide a RecordRepository backed by the current DB session."""
    return SqlAlchemyRecordRepository(session)


def get_action_item_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionItemRepository:
    """Provide an ActionItemRepository backed by the current DB session."""
    return SqlAlchemyActionItemRepository(session)


def get_schedule_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScheduleRepository:
    """Provide a ScheduleRepository backed by the current DB session."""
    return SqlAlchemyScheduleRepository(session)


# ---------------------------------------------------------------------------
# Use case providers
# ---------------------------------------------------------------------------


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


def get_create_record_from_schedule_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateRecordFromScheduleUseCase:
    """Provide a CreateRecordFromScheduleUseCase with all dependencies injected."""
    return CreateRecordFromScheduleUseCase(
        record_repository=record_repo,
        schedule_repository=schedule_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_update_memo_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> UpdateMemoUseCase:
    """Provide an UpdateMemoUseCase with all dependencies injected."""
    return UpdateMemoUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_confirm_agenda_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> ConfirmAgendaUseCase:
    """Provide a ConfirmAgendaUseCase with all dependencies injected."""
    return ConfirmAgendaUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_add_action_item_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(get_action_item_repository)
    ],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddActionItemUseCase:
    """Provide an AddActionItemUseCase with all dependencies injected."""
    return AddActionItemUseCase(
        record_repository=record_repo,
        action_item_repository=action_item_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_delete_action_item_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(get_action_item_repository)
    ],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> DeleteActionItemUseCase:
    """Provide a DeleteActionItemUseCase with all dependencies injected."""
    return DeleteActionItemUseCase(
        record_repository=record_repo,
        action_item_repository=action_item_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_save_draft_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SaveDraftUseCase:
    """Provide a SaveDraftUseCase with all dependencies injected."""
    return SaveDraftUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )
