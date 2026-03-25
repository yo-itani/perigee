"""DI providers for the Record context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordUseCase,
)
from contexts.record.application.publish_record import (
    PublishRecordUseCase,
)
from contexts.record.application.set_viewers import (
    SetViewersUseCase,
)
from contexts.record.application.suggest_default_viewers import (
    SuggestDefaultViewersUseCase,
)
from contexts.record.domain.captain_query_service import CaptainQueryService
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


def get_captain_query_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CaptainQueryService:
    """Provide a CaptainQueryService backed by the Workspace context."""
    from contexts.record.infrastructure.workspace_captain_query_service import (
        WorkspaceCaptainQueryService,
    )
    from contexts.workspace.infrastructure.sqlalchemy_workspace_repository import (
        SqlAlchemyWorkspaceRepository,
    )

    workspace_repo = SqlAlchemyWorkspaceRepository(session)
    return WorkspaceCaptainQueryService(workspace_repo=workspace_repo)


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


def get_suggest_default_viewers_use_case(
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    captain_query_service: Annotated[
        CaptainQueryService, Depends(get_captain_query_service)
    ],
) -> SuggestDefaultViewersUseCase:
    """Provide a SuggestDefaultViewersUseCase with all dependencies injected."""
    return SuggestDefaultViewersUseCase(
        record_repository=record_repo,
        captain_query_service=captain_query_service,
    )


def get_set_viewers_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SetViewersUseCase:
    """Provide a SetViewersUseCase with all dependencies injected."""
    return SetViewersUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )


def get_publish_record_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    record_repo: Annotated[RecordRepository, Depends(get_record_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> PublishRecordUseCase:
    """Provide a PublishRecordUseCase with all dependencies injected."""
    return PublishRecordUseCase(
        record_repository=record_repo,
        unit_of_work=uow,
        event_dispatcher=event_dispatcher,
    )
