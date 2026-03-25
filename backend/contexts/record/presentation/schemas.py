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
