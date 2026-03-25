"""Pydantic request/response schemas for the Record context API."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

# ---------------------------------------------------------------------------
# Post-hoc record -- POST /records/post-hoc
# ---------------------------------------------------------------------------


class CreatePostHocRecordRequest(BaseModel):
    """Request body for POST /records/post-hoc."""

    counterpart_id: UUID
    conducted_at: AwareDatetime


class CreatePostHocRecordResponse(BaseModel):
    """Response body for POST /records/post-hoc."""

    record_id: UUID


# ---------------------------------------------------------------------------
# Record detail -- GET /records/{record_id}
# ---------------------------------------------------------------------------


class ActionItemSchema(BaseModel):
    """Action item within a record detail response."""

    action_item_id: UUID
    title: str
    is_completed: bool
    counterpart_id: UUID
    created_at: datetime


class GetRecordDetailResponse(BaseModel):
    """Response body for GET /records/{record_id}."""

    record_id: UUID
    organizer_id: UUID
    counterpart_id: UUID
    schedule_id: UUID | None
    memo: str
    status: str
    confirmed_agenda_ids: list[UUID]
    action_items: list[ActionItemSchema]
    conducted_at: datetime
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Comments -- GET /records/{record_id}/comments
# ---------------------------------------------------------------------------


class CommentSchema(BaseModel):
    """Single comment in a comment list response."""

    comment_id: UUID
    author_id: UUID
    body: str
    created_at: datetime


class ListRecordCommentsResponse(BaseModel):
    """Response body for GET /records/{record_id}/comments."""

    comments: list[CommentSchema]


# ---------------------------------------------------------------------------
# Viewers -- GET /records/{record_id}/viewers
# ---------------------------------------------------------------------------


class GetViewersResponse(BaseModel):
    """Response body for GET /records/{record_id}/viewers."""

    viewer_ids: list[UUID]


# ---------------------------------------------------------------------------
# Add comment -- POST /records/{record_id}/comments
# ---------------------------------------------------------------------------


class AddCommentRequest(BaseModel):
    """Request body for POST /records/{record_id}/comments."""

    body: str


class AddCommentResponse(BaseModel):
    """Response body for POST /records/{record_id}/comments."""

    comment_id: UUID


# ---------------------------------------------------------------------------
# Complete action item -- POST /action-items/{action_item_id}/complete
# ---------------------------------------------------------------------------


class CompleteActionItemResponse(BaseModel):
    """Response body for POST /action-items/{action_item_id}/complete."""

    action_item_id: UUID


# ---------------------------------------------------------------------------
# 1on1 history -- GET /records/history
# ---------------------------------------------------------------------------


class OneOnOneHistoryItemSchema(BaseModel):
    """Single item in the 1-on-1 history list."""

    record_id: UUID
    organizer_id: UUID
    counterpart_id: UUID
    conducted_at: datetime
    memo_excerpt: str
    schedule_id: UUID | None


class ListOneOnOneHistoryResponse(BaseModel):
    """Response body for GET /records/history."""

    items: list[OneOnOneHistoryItemSchema]
    total_count: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Suggested viewers -- GET /records/{id}/suggested-viewers
# ---------------------------------------------------------------------------


class SuggestedViewersResponse(BaseModel):
    """Response body for GET /records/{id}/suggested-viewers."""

    suggested_viewer_ids: list[UUID]


# ---------------------------------------------------------------------------
# Set viewers -- PUT /records/{id}/viewers
# ---------------------------------------------------------------------------


class SetViewersRequest(BaseModel):
    """Request body for PUT /records/{id}/viewers."""

    viewer_ids: list[UUID]


class SetViewersResponse(BaseModel):
    """Response body for PUT /records/{id}/viewers."""

    record_id: UUID


# ---------------------------------------------------------------------------
# Publish record -- POST /records/{id}/publish
# ---------------------------------------------------------------------------


class PublishRecordRequest(BaseModel):
    """Request body for POST /records/{id}/publish."""

    viewer_ids: list[UUID]


class PublishRecordResponse(BaseModel):
    """Response body for POST /records/{id}/publish."""

    record_id: UUID
