"""FastAPI router for the Record context (post-hoc record endpoint)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordInput,
    CreatePostHocRecordUseCase,
)
from contexts.record.presentation.dependencies import (
    get_create_post_hoc_record_use_case,
)
from contexts.record.presentation.schemas import (
    CreatePostHocRecordRequest,
    CreatePostHocRecordResponse,
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
