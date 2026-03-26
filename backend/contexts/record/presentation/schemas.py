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
# Create record from schedule -- POST /records/from-schedule
# ---------------------------------------------------------------------------


class CreateRecordFromScheduleRequest(BaseModel):
    """Request body for POST /records/from-schedule."""

    schedule_id: UUID
    conducted_at: AwareDatetime


class CreateRecordFromScheduleResponse(BaseModel):
    """Response body for POST /records/from-schedule."""

    record_id: UUID


# ---------------------------------------------------------------------------
# Update memo -- PUT /records/{id}/memo
# ---------------------------------------------------------------------------


class UpdateMemoRequest(BaseModel):
    """Request body for PUT /records/{id}/memo."""

    memo: str


class UpdateMemoResponse(BaseModel):
    """Response body for PUT /records/{id}/memo."""

    record_id: UUID


# ---------------------------------------------------------------------------
# Confirm agenda -- POST /records/{id}/agendas/{agenda_id}/confirm
# ---------------------------------------------------------------------------


class ConfirmAgendaResponse(BaseModel):
    """Response body for POST /records/{id}/agendas/{agenda_id}/confirm."""

    record_id: UUID
    agenda_id: UUID


# ---------------------------------------------------------------------------
# Add action item -- POST /records/{id}/action-items
# ---------------------------------------------------------------------------


class AddActionItemRequest(BaseModel):
    """Request body for POST /records/{id}/action-items."""

    title: str


class AddActionItemResponse(BaseModel):
    """Response body for POST /records/{id}/action-items."""

    action_item_id: UUID


# ---------------------------------------------------------------------------
# Delete action item -- DELETE /records/{id}/action-items/{action_item_id}
# ---------------------------------------------------------------------------


class DeleteActionItemResponse(BaseModel):
    """Response body for DELETE /records/{id}/action-items/{action_item_id}."""

    action_item_id: UUID


# ---------------------------------------------------------------------------
# Save draft -- POST /records/{id}/save-draft
# ---------------------------------------------------------------------------


class SaveDraftResponse(BaseModel):
    """Response body for POST /records/{id}/save-draft."""

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


# ---------------------------------------------------------------------------
# Draft records -- GET /records/drafts
# ---------------------------------------------------------------------------


class DraftRecordItemSchema(BaseModel):
    """A single item in the draft records response."""

    record_id: UUID
    counterpart_id: UUID
    conducted_at: AwareDatetime
    memo_excerpt: str
    created_at: AwareDatetime
    schedule_id: UUID | None


class ListDraftRecordsResponse(BaseModel):
    """Response body for GET /records/drafts."""

    items: list[DraftRecordItemSchema]


# ---------------------------------------------------------------------------
# Mark record as viewed -- POST /records/{record_id}/viewed
# ---------------------------------------------------------------------------


class MarkRecordAsViewedResponse(BaseModel):
    """Response body for POST /records/{record_id}/viewed."""

    record_id: UUID
