"""Pydantic request/response schemas for the Record context API."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel

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
