"""Pydantic request/response schemas for the Preparation context API."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, field_validator

from foundation.datetime_utils import normalize_to_utc

# ---------------------------------------------------------------------------
# ScheduleGroup -- POST /schedule-groups
# ---------------------------------------------------------------------------


class CounterpartScheduleSchema(BaseModel):
    """Per-counterpart scheduling parameters."""

    counterpart_id: UUID
    scheduled_at: AwareDatetime

    @field_validator("scheduled_at")
    @classmethod
    def _normalize_scheduled_at_to_utc(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)


class CreateScheduleGroupRequest(BaseModel):
    """Request body for POST /schedule-groups."""

    title: str
    counterpart_schedules: list[CounterpartScheduleSchema]
    agenda_topics: list[str] | None = None
    template_id: UUID | None = None


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
    scheduled_at: AwareDatetime
    title: str

    @field_validator("scheduled_at")
    @classmethod
    def _normalize_scheduled_at_to_utc(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)


class CreateScheduleResponse(BaseModel):
    """Response body for POST /schedules."""

    schedule_id: UUID


# ---------------------------------------------------------------------------
# Consultation request -- POST /schedules/consultation-request
# ---------------------------------------------------------------------------


class SendConsultationRequestRequest(BaseModel):
    """Request body for POST /schedules/consultation-request."""

    organizer_id: UUID
    scheduled_at: AwareDatetime
    title: str
    agenda_topics: list[str]

    @field_validator("scheduled_at")
    @classmethod
    def _normalize_scheduled_at_to_utc(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)


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
    created_at: AwareDatetime
    updated_at: AwareDatetime


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
    created_at: AwareDatetime
    updated_at: AwareDatetime


class SaveTemplateRequest(BaseModel):
    """Request body for POST /templates."""

    name: str
    default_counterpart_ids: list[UUID]
    agenda_topics: list[str]


class SaveTemplateResponse(BaseModel):
    """Response body for POST /templates."""

    template_id: UUID


# ---------------------------------------------------------------------------
# Upcoming schedules -- GET /schedules/upcoming
# ---------------------------------------------------------------------------


class UpcomingScheduleItemSchema(BaseModel):
    """A single item in the upcoming schedules response."""

    schedule_id: UUID
    organizer_id: UUID
    counterpart_id: UUID
    scheduled_at: AwareDatetime
    status: str
    title: str
    schedule_group_id: UUID | None


class ListUpcomingSchedulesResponse(BaseModel):
    """Response body for GET /schedules/upcoming."""

    schedules: list[UpcomingScheduleItemSchema]


# ---------------------------------------------------------------------------
# Schedule detail -- GET /schedules/{id}
# ---------------------------------------------------------------------------


class GetScheduleDetailResponse(BaseModel):
    """Response body for GET /schedules/{schedule_id}."""

    schedule_id: UUID
    organizer_id: UUID
    counterpart_id: UUID
    title: str
    scheduled_at: AwareDatetime
    status: str
    schedule_group_id: UUID | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


# ---------------------------------------------------------------------------
# Schedule agendas -- GET /schedules/{id}/agendas
# ---------------------------------------------------------------------------


class AgendaCommentSchema(BaseModel):
    """A single comment within an agenda."""

    comment_id: UUID
    author_id: UUID
    body: str
    created_at: AwareDatetime


class AgendaItemSchema(BaseModel):
    """A single agenda item with its comments."""

    agenda_id: UUID
    topic: str
    added_by: UUID
    added_by_tag: str
    comments: list[AgendaCommentSchema]
    created_at: AwareDatetime


class ListScheduleAgendasResponse(BaseModel):
    """Response body for GET /schedules/{schedule_id}/agendas."""

    agendas: list[AgendaItemSchema]


# ---------------------------------------------------------------------------
# Schedule operations -- reschedule, rename
# ---------------------------------------------------------------------------


class RescheduleRequest(BaseModel):
    """Request body for POST /schedules/{schedule_id}/reschedule."""

    new_scheduled_at: AwareDatetime

    @field_validator("new_scheduled_at")
    @classmethod
    def _normalize_new_scheduled_at_to_utc(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)


class RenameScheduleRequest(BaseModel):
    """Request body for PUT /schedules/{schedule_id}/title."""

    title: str


# ---------------------------------------------------------------------------
# Agenda operations -- add, add comment
# ---------------------------------------------------------------------------


class AddAgendaRequest(BaseModel):
    """Request body for POST /schedules/{schedule_id}/agendas."""

    topic: str


class AddAgendaResponse(BaseModel):
    """Response body for POST /schedules/{schedule_id}/agendas."""

    agenda_id: UUID


class AddAgendaCommentRequest(BaseModel):
    """Request body for POST /agendas/{agenda_id}/comments."""

    body: str


class AddAgendaCommentResponse(BaseModel):
    """Response body for POST /agendas/{agenda_id}/comments."""

    comment_id: UUID


# ---------------------------------------------------------------------------
# Cross-context reads -- last session summary, pending action items
# ---------------------------------------------------------------------------


class ActionItemSummarySchema(BaseModel):
    """A single action item in the session summary."""

    action_item_id: UUID
    content: str
    is_completed: bool
    created_at: AwareDatetime


class GetLastSessionSummaryResponse(BaseModel):
    """Response body for GET /records/last-summary."""

    record_id: UUID
    conducted_at: AwareDatetime
    memo_excerpt: str
    action_items: list[ActionItemSummarySchema]


class PendingActionItemSchema(BaseModel):
    """A single pending action item."""

    action_item_id: UUID
    content: str
    created_at: AwareDatetime
    record_id: UUID
    organizer_id: UUID
    conducted_at: AwareDatetime


class ListPendingActionItemsResponse(BaseModel):
    """Response body for GET /action-items/pending/{counterpart_id}."""

    items: list[PendingActionItemSchema]


class AllPendingActionItemSchema(BaseModel):
    """A single pending action item in the all-counterpart overview."""

    action_item_id: UUID
    content: str
    created_at: AwareDatetime
    record_id: UUID
    counterpart_id: UUID
    conducted_at: AwareDatetime


class ListAllPendingActionItemsResponse(BaseModel):
    """Response body for GET /action-items/pending."""

    items: list[AllPendingActionItemSchema]
