"""FastAPI router for the Record context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.application.add_action_item import (
    AddActionItemInput,
    AddActionItemUseCase,
)
from contexts.record.application.add_comment import (
    AddCommentInput,
    AddCommentUseCase,
)
from contexts.record.application.complete_action_item import (
    CompleteActionItemInput,
    CompleteActionItemUseCase,
)
from contexts.record.application.confirm_agenda import (
    ConfirmAgendaInput,
    ConfirmAgendaUseCase,
)
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordInput,
    CreatePostHocRecordUseCase,
)
from contexts.record.application.create_record_from_schedule import (
    CreateRecordFromScheduleInput,
    CreateRecordFromScheduleUseCase,
)
from contexts.record.application.delete_action_item import (
    DeleteActionItemInput,
    DeleteActionItemUseCase,
)
from contexts.record.application.get_record_detail import (
    GetRecordDetailInput,
    GetRecordDetailUseCase,
)
from contexts.record.application.get_viewers import (
    GetViewersInput,
    GetViewersUseCase,
)
from contexts.record.application.list_oneonone_history import (
    ListOneOnOneHistoryInput,
    ListOneOnOneHistoryService,
)
from contexts.record.application.list_record_comments import (
    ListRecordCommentsInput,
    ListRecordCommentsUseCase,
)
from contexts.record.application.publish_record import (
    PublishRecordInput,
    PublishRecordUseCase,
)
from contexts.record.application.save_draft import (
    SaveDraftInput,
    SaveDraftUseCase,
)
from contexts.record.application.set_viewers import (
    SetViewersInput,
    SetViewersUseCase,
)
from contexts.record.application.suggest_default_viewers import (
    SuggestDefaultViewersInput,
    SuggestDefaultViewersUseCase,
)
from contexts.record.application.update_memo import (
    UpdateMemoInput,
    UpdateMemoUseCase,
)
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.memo import Memo
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle, RecordId
from contexts.record.presentation.dependencies import (
    get_add_action_item_use_case,
    get_add_comment_use_case,
    get_complete_action_item_use_case,
    get_confirm_agenda_use_case,
    get_create_post_hoc_record_use_case,
    get_create_record_from_schedule_use_case,
    get_delete_action_item_use_case,
    get_get_record_detail_use_case,
    get_get_viewers_use_case,
    get_list_oneonone_history_service,
    get_list_record_comments_use_case,
    get_publish_record_use_case,
    get_save_draft_use_case,
    get_set_viewers_use_case,
    get_suggest_default_viewers_use_case,
    get_update_memo_use_case,
)
from contexts.record.presentation.schemas import (
    ActionItemSchema,
    AddActionItemRequest,
    AddActionItemResponse,
    AddCommentRequest,
    AddCommentResponse,
    CommentSchema,
    CompleteActionItemResponse,
    ConfirmAgendaResponse,
    CreatePostHocRecordRequest,
    CreatePostHocRecordResponse,
    CreateRecordFromScheduleRequest,
    CreateRecordFromScheduleResponse,
    DeleteActionItemResponse,
    GetRecordDetailResponse,
    GetViewersResponse,
    ListOneOnOneHistoryResponse,
    ListRecordCommentsResponse,
    OneOnOneHistoryItemSchema,
    PublishRecordRequest,
    PublishRecordResponse,
    SaveDraftResponse,
    SetViewersRequest,
    SetViewersResponse,
    SuggestedViewersResponse,
    UpdateMemoRequest,
    UpdateMemoResponse,
)
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /records/post-hoc
# ---------------------------------------------------------------------------


@router.post(
    "/records/post-hoc",
    response_model=CreatePostHocRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post_hoc_record(
    body: CreatePostHocRecordRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        CreatePostHocRecordUseCase, Depends(get_create_post_hoc_record_use_case)
    ],
) -> CreatePostHocRecordResponse:
    """Create a post-hoc record (without prior scheduling)."""
    input_dto = CreatePostHocRecordInput(
        actor_id=current_user_id,
        organizer_id=current_user_id,
        counterpart_id=UserId(value=body.counterpart_id),
        conducted_at=body.conducted_at,
    )
    output = await use_case.execute(input_dto)
    return CreatePostHocRecordResponse(record_id=output.record_id.value)


# ---------------------------------------------------------------------------
# POST /records/from-schedule
# ---------------------------------------------------------------------------


@router.post(
    "/records/from-schedule",
    response_model=CreateRecordFromScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_record_from_schedule(
    body: CreateRecordFromScheduleRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        CreateRecordFromScheduleUseCase,
        Depends(get_create_record_from_schedule_use_case),
    ],
) -> CreateRecordFromScheduleResponse:
    """Create a record from a confirmed schedule."""
    input_dto = CreateRecordFromScheduleInput(
        schedule_id=ScheduleId(value=body.schedule_id),
        actor_id=current_user_id,
        conducted_at=body.conducted_at,
    )
    output = await use_case.execute(input_dto)
    return CreateRecordFromScheduleResponse(record_id=output.record_id.value)


# ---------------------------------------------------------------------------
# PUT /records/{id}/memo
# ---------------------------------------------------------------------------


@router.put(
    "/records/{record_id}/memo",
    response_model=UpdateMemoResponse,
)
async def update_memo(
    record_id: UUID,
    body: UpdateMemoRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[UpdateMemoUseCase, Depends(get_update_memo_use_case)],
) -> UpdateMemoResponse:
    """Update the memo of a record."""
    input_dto = UpdateMemoInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
        memo=Memo(body.memo),
    )
    output = await use_case.execute(input_dto)
    return UpdateMemoResponse(record_id=output.record_id.value)


# ---------------------------------------------------------------------------
# POST /records/{id}/agendas/{agenda_id}/confirm
# ---------------------------------------------------------------------------


@router.post(
    "/records/{record_id}/agendas/{agenda_id}/confirm",
    response_model=ConfirmAgendaResponse,
)
async def confirm_agenda(
    record_id: UUID,
    agenda_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[ConfirmAgendaUseCase, Depends(get_confirm_agenda_use_case)],
) -> ConfirmAgendaResponse:
    """Confirm (check) an agenda item during a 1-on-1."""
    input_dto = ConfirmAgendaInput(
        record_id=RecordId(value=record_id),
        agenda_id=AgendaId(value=agenda_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return ConfirmAgendaResponse(
        record_id=output.record_id.value,
        agenda_id=output.agenda_id.value,
    )


# ---------------------------------------------------------------------------
# POST /records/{id}/action-items
# ---------------------------------------------------------------------------


@router.post(
    "/records/{record_id}/action-items",
    response_model=AddActionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_action_item(
    record_id: UUID,
    body: AddActionItemRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[AddActionItemUseCase, Depends(get_add_action_item_use_case)],
) -> AddActionItemResponse:
    """Add an action item to a record."""
    input_dto = AddActionItemInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
        title=ActionItemTitle(body.title),
    )
    output = await use_case.execute(input_dto)
    return AddActionItemResponse(action_item_id=output.action_item_id.value)


# ---------------------------------------------------------------------------
# DELETE /records/{id}/action-items/{action_item_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/records/{record_id}/action-items/{action_item_id}",
    response_model=DeleteActionItemResponse,
)
async def delete_action_item(
    record_id: UUID,
    action_item_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        DeleteActionItemUseCase, Depends(get_delete_action_item_use_case)
    ],
) -> DeleteActionItemResponse:
    """Delete an action item from a record."""
    input_dto = DeleteActionItemInput(
        record_id=RecordId(value=record_id),
        action_item_id=ActionItemId(value=action_item_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return DeleteActionItemResponse(action_item_id=output.action_item_id.value)


# ---------------------------------------------------------------------------
# POST /records/{id}/save-draft
# ---------------------------------------------------------------------------


@router.post(
    "/records/{record_id}/save-draft",
    response_model=SaveDraftResponse,
)
async def save_draft(
    record_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[SaveDraftUseCase, Depends(get_save_draft_use_case)],
) -> SaveDraftResponse:
    """Save a record as draft."""
    input_dto = SaveDraftInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return SaveDraftResponse(record_id=output.record_id.value)


# ---------------------------------------------------------------------------
# Record viewer endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/records/history",
    response_model=ListOneOnOneHistoryResponse,
)
async def list_oneonone_history(
    organizer_id: Annotated[UUID, Query()],
    counterpart_id: Annotated[UUID, Query()],
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        ListOneOnOneHistoryService, Depends(get_list_oneonone_history_service)
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> ListOneOnOneHistoryResponse:
    """List 1-on-1 history for an organizer-counterpart pair."""
    input_dto = ListOneOnOneHistoryInput(
        actor_id=current_user_id,
        organizer_id=UserId(value=organizer_id),
        counterpart_id=UserId(value=counterpart_id),
        offset=offset,
        limit=limit,
    )
    output = await service.execute(input_dto)
    return ListOneOnOneHistoryResponse(
        items=[
            OneOnOneHistoryItemSchema(
                record_id=item.record_id.value,
                organizer_id=item.organizer_id.value,
                counterpart_id=item.counterpart_id.value,
                conducted_at=item.conducted_at,
                memo_excerpt=item.memo_excerpt,
                schedule_id=item.schedule_id.value if item.schedule_id else None,
            )
            for item in output.items
        ],
        total_count=output.total_count,
    )


@router.get(
    "/records/{record_id}",
    response_model=GetRecordDetailResponse,
)
async def get_record_detail(
    record_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        GetRecordDetailUseCase, Depends(get_get_record_detail_use_case)
    ],
) -> GetRecordDetailResponse:
    """Get record detail."""
    input_dto = GetRecordDetailInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return GetRecordDetailResponse(
        record_id=output.record_id.value,
        organizer_id=output.organizer_id.value,
        counterpart_id=output.counterpart_id.value,
        schedule_id=output.schedule_id.value if output.schedule_id else None,
        memo=output.memo,
        status=output.status.value,
        confirmed_agenda_ids=[aid.value for aid in output.confirmed_agenda_ids],
        action_items=[
            ActionItemSchema(
                action_item_id=ai.action_item_id.value,
                title=ai.title,
                is_completed=ai.is_completed,
                counterpart_id=ai.counterpart_id.value,
                created_at=ai.created_at,
            )
            for ai in output.action_items
        ],
        conducted_at=output.conducted_at,
        created_at=output.created_at,
        updated_at=output.updated_at,
    )


@router.get(
    "/records/{record_id}/comments",
    response_model=ListRecordCommentsResponse,
)
async def list_record_comments(
    record_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        ListRecordCommentsUseCase, Depends(get_list_record_comments_use_case)
    ],
) -> ListRecordCommentsResponse:
    """List comments for a published record."""
    input_dto = ListRecordCommentsInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return ListRecordCommentsResponse(
        comments=[
            CommentSchema(
                comment_id=c.comment_id.value,
                author_id=c.author_id.value,
                body=c.body,
                created_at=c.created_at,
            )
            for c in output.comments
        ]
    )


@router.get(
    "/records/{record_id}/viewers",
    response_model=GetViewersResponse,
)
async def get_viewers(
    record_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[GetViewersUseCase, Depends(get_get_viewers_use_case)],
) -> GetViewersResponse:
    """Get viewers for a record."""
    input_dto = GetViewersInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return GetViewersResponse(
        viewer_ids=[v.value for v in output.viewer_ids],
    )


@router.post(
    "/records/{record_id}/comments",
    response_model=AddCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    record_id: UUID,
    body: AddCommentRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[AddCommentUseCase, Depends(get_add_comment_use_case)],
) -> AddCommentResponse:
    """Add a comment to a published record."""
    input_dto = AddCommentInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
        body=CommentBody(body.body),
    )
    output = await use_case.execute(input_dto)
    return AddCommentResponse(comment_id=output.comment_id.value)


@router.post(
    "/action-items/{action_item_id}/complete",
    response_model=CompleteActionItemResponse,
)
async def complete_action_item(
    action_item_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        CompleteActionItemUseCase, Depends(get_complete_action_item_use_case)
    ],
) -> CompleteActionItemResponse:
    """Complete an action item."""
    input_dto = CompleteActionItemInput(
        action_item_id=ActionItemId(value=action_item_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return CompleteActionItemResponse(action_item_id=output.action_item_id.value)


# ---------------------------------------------------------------------------
# Publishing flow
# ---------------------------------------------------------------------------


@router.get(
    "/records/{record_id}/suggested-viewers",
    response_model=SuggestedViewersResponse,
)
async def get_suggested_viewers(
    record_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[
        SuggestDefaultViewersUseCase, Depends(get_suggest_default_viewers_use_case)
    ],
) -> SuggestedViewersResponse:
    """Suggest default viewers based on the counterpart's Captain hierarchy."""
    input_dto = SuggestDefaultViewersInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
    )
    output = await use_case.execute(input_dto)
    return SuggestedViewersResponse(
        suggested_viewer_ids=[uid.value for uid in output.suggested_viewer_ids],
    )


@router.put(
    "/records/{record_id}/viewers",
    response_model=SetViewersResponse,
)
async def set_viewers(
    record_id: UUID,
    body: SetViewersRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[SetViewersUseCase, Depends(get_set_viewers_use_case)],
) -> SetViewersResponse:
    """Set the viewers list for a record."""
    input_dto = SetViewersInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
        viewer_ids=[UserId(value=vid) for vid in body.viewer_ids],
    )
    output = await use_case.execute(input_dto)
    return SetViewersResponse(record_id=output.record_id.value)


@router.post(
    "/records/{record_id}/publish",
    response_model=PublishRecordResponse,
)
async def publish_record(
    record_id: UUID,
    body: PublishRecordRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    use_case: Annotated[PublishRecordUseCase, Depends(get_publish_record_use_case)],
) -> PublishRecordResponse:
    """Publish a record (DRAFT -> PUBLISHED)."""
    input_dto = PublishRecordInput(
        record_id=RecordId(value=record_id),
        actor_id=current_user_id,
        viewer_ids=[UserId(value=vid) for vid in body.viewer_ids],
    )
    output = await use_case.execute(input_dto)
    return PublishRecordResponse(record_id=output.record_id.value)
