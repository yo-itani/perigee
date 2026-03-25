"""Pydantic request/response schemas for the Preparation context API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# ScheduleGroup -- POST /schedule-groups
# ---------------------------------------------------------------------------


class CounterpartScheduleSchema(BaseModel):
    """Per-counterpart scheduling parameters."""

    counterpart_id: UUID
    scheduled_at: datetime


class CreateScheduleGroupRequest(BaseModel):
    """Request body for POST /schedule-groups."""

    title: str
    counterpart_schedules: list[CounterpartScheduleSchema]
    agenda_topics: list[str] | None = None
    template_id: str | None = None


class CreateScheduleGroupResponse(BaseModel):
    """Response body for POST /schedule-groups."""

    schedule_group_id: UUID


# ---------------------------------------------------------------------------
# ScheduleGroup from template -- POST /schedule-groups/from-template
# ---------------------------------------------------------------------------


class CreateScheduleGroupFromTemplateRequest(BaseModel):
    """Request body for POST /schedule-groups/from-template."""

    template_id: UUID
    title: str
    counterpart_schedules: list[CounterpartScheduleSchema]


class CreateScheduleGroupFromTemplateResponse(BaseModel):
    """Response body for POST /schedule-groups/from-template."""

    schedule_group_id: UUID


# ---------------------------------------------------------------------------
# ScheduleGroup from past -- POST /schedule-groups/from-past
# ---------------------------------------------------------------------------


class CreateScheduleGroupFromPastRequest(BaseModel):
    """Request body for POST /schedule-groups/from-past."""

    source_schedule_group_id: UUID
    title: str
    counterpart_schedules: list[CounterpartScheduleSchema]


class CreateScheduleGroupFromPastResponse(BaseModel):
    """Response body for POST /schedule-groups/from-past."""

    schedule_group_id: UUID


# ---------------------------------------------------------------------------
# Schedule -- POST /schedules
# ---------------------------------------------------------------------------


class CreateScheduleRequest(BaseModel):
    """Request body for POST /schedules."""

    counterpart_id: UUID
    scheduled_at: datetime
    title: str


class CreateScheduleResponse(BaseModel):
    """Response body for POST /schedules."""

    schedule_id: UUID


# ---------------------------------------------------------------------------
# Consultation request -- POST /schedules/consultation-request
# ---------------------------------------------------------------------------


class SendConsultationRequestRequest(BaseModel):
    """Request body for POST /schedules/consultation-request."""

    organizer_id: UUID
    scheduled_at: datetime
    title: str
    agenda_topics: list[str]


class SendConsultationRequestResponse(BaseModel):
    """Response body for POST /schedules/consultation-request."""

    schedule_id: UUID


# ---------------------------------------------------------------------------
# Template -- GET /templates, GET /templates/{id}, POST /templates
# ---------------------------------------------------------------------------


class TemplateListItemSchema(BaseModel):
    """A single item in the template list response."""

    template_id: UUID
    name: str
    default_counterpart_ids: list[UUID]
    agenda_topics: list[str]
    created_at: datetime
    updated_at: datetime


class ListTemplatesResponse(BaseModel):
    """Response body for GET /templates."""

    templates: list[TemplateListItemSchema]


class GetTemplateResponse(BaseModel):
    """Response body for GET /templates/{template_id}."""

    template_id: UUID
    organizer_id: UUID
    name: str
    default_counterpart_ids: list[UUID]
    agenda_topics: list[str]
    created_at: datetime
    updated_at: datetime


class SaveTemplateRequest(BaseModel):
    """Request body for POST /templates."""

    name: str
    default_counterpart_ids: list[UUID]
    agenda_topics: list[str]


class SaveTemplateResponse(BaseModel):
    """Response body for POST /templates."""

    template_id: UUID
