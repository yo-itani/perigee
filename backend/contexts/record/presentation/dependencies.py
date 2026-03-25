"""DI providers for the Record context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.record.application.add_comment import AddCommentUseCase
from contexts.record.application.complete_action_item import CompleteActionItemUseCase
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordUseCase,
)
from contexts.record.application.get_record_detail import GetRecordDetailUseCase
from contexts.record.application.get_viewers import GetViewersUseCase
from contexts.record.application.list_oneonone_history import (
    ListOneOnOneHistoryService,
)
from contexts.record.application.list_record_comments import (
    ListRecordCommentsUseCase,
)
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.comment_repository import CommentRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.infrastructure.sqlalchemy_action_item_repository import (
    SqlAlchemyActionItemRepository,
)
from contexts.record.infrastructure.sqlalchemy_comment_repository import (
    SqlAlchemyCommentRepository,
)
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


def get_comment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentRepository:
    """Provide a CommentRepository backed by the current DB session."""
    return SqlAlchemyCommentRepository(session)


def get_action_item_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionItemRepository:
    """Provide an ActionItemRepository backed by the current DB session."""
    return SqlAlchemyActionItemRepository(session)


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


def get_get_record_detail_use_case(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(get_action_item_repository)
    ],
) -> GetRecordDetailUseCase:
    """Provide a GetRecordDetailUseCase with all dependencies injected."""
    return GetRecordDetailUseCase(
        record_repository=record_repo,
        action_item_repository=action_item_repo,
    )


def get_list_record_comments_use_case(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    comment_repo: Annotated[CommentRepository, Depends(get_comment_repository)],
) -> ListRecordCommentsUseCase:
    """Provide a ListRecordCommentsUseCase with all dependencies injected."""
    return ListRecordCommentsUseCase(
        record_repository=record_repo,
        comment_repository=comment_repo,
    )


def get_get_viewers_use_case(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
) -> GetViewersUseCase:
    """Provide a GetViewersUseCase with all dependencies injected."""
    return GetViewersUseCase(
        record_repository=record_repo,
    )


def get_add_comment_use_case(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    comment_repo: Annotated[CommentRepository, Depends(get_comment_repository)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddCommentUseCase:
    """Provide an AddCommentUseCase with all dependencies injected."""
    return AddCommentUseCase(
        record_repository=record_repo,
        comment_repository=comment_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_complete_action_item_use_case(
    action_item_repo: Annotated[
        ActionItemRepository, Depends(get_action_item_repository)
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CompleteActionItemUseCase:
    """Provide a CompleteActionItemUseCase with all dependencies injected."""
    return CompleteActionItemUseCase(
        action_item_repository=action_item_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_list_oneonone_history_service(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
) -> ListOneOnOneHistoryService:
    """Provide a ListOneOnOneHistoryService with all dependencies injected."""
    return ListOneOnOneHistoryService(
        record_repository=record_repo,
    )
