"""FastAPI router for the Record context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordInput,
    CreatePostHocRecordUseCase,
)
from contexts.record.application.publish_record import (
    PublishRecordInput,
    PublishRecordUseCase,
)
from contexts.record.application.set_viewers import (
    SetViewersInput,
    SetViewersUseCase,
)
from contexts.record.application.suggest_default_viewers import (
    SuggestDefaultViewersInput,
    SuggestDefaultViewersUseCase,
)
from contexts.record.domain.value_objects import RecordId
from contexts.record.presentation.dependencies import (
    get_create_post_hoc_record_use_case,
    get_publish_record_use_case,
    get_set_viewers_use_case,
    get_suggest_default_viewers_use_case,
)
from contexts.record.presentation.schemas import (
    CreatePostHocRecordRequest,
    CreatePostHocRecordResponse,
    PublishRecordRequest,
    PublishRecordResponse,
    SetViewersRequest,
    SetViewersResponse,
    SuggestedViewersResponse,
)
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

router = APIRouter()


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
