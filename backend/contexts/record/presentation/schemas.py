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
