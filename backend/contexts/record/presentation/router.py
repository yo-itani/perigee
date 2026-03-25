"""FastAPI router for the Record context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.application.add_action_item import (
    AddActionItemInput,
    AddActionItemUseCase,
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
from contexts.record.application.save_draft import (
    SaveDraftInput,
    SaveDraftUseCase,
)
from contexts.record.application.update_memo import (
    UpdateMemoInput,
    UpdateMemoUseCase,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.value_objects import ActionItemId, ActionItemTitle, RecordId
from contexts.record.presentation.dependencies import (
    get_add_action_item_use_case,
    get_confirm_agenda_use_case,
    get_create_post_hoc_record_use_case,
    get_create_record_from_schedule_use_case,
    get_delete_action_item_use_case,
    get_save_draft_use_case,
    get_update_memo_use_case,
)
from contexts.record.presentation.schemas import (
    AddActionItemRequest,
    AddActionItemResponse,
    ConfirmAgendaResponse,
    CreatePostHocRecordRequest,
    CreatePostHocRecordResponse,
    CreateRecordFromScheduleRequest,
    CreateRecordFromScheduleResponse,
    DeleteActionItemResponse,
    SaveDraftResponse,
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
