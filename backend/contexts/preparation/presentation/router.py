"""FastAPI router for the Preparation context (setup screen endpoints)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contexts.preparation.application.create_schedule_group_from_past_service import (
    CreateScheduleGroupFromPastInput,
    CreateScheduleGroupFromPastService,
    PastCounterpartSchedule,
)
from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    CreateScheduleGroupFromTemplateInput,
    CreateScheduleGroupFromTemplateService,
    TemplateCounterpartSchedule,
)
from contexts.preparation.application.create_schedule_group_service import (
    CounterpartSchedule,
    CreateScheduleGroupInput,
    CreateScheduleGroupService,
)
from contexts.preparation.application.create_schedule_service import (
    CreateScheduleInput,
    CreateScheduleService,
)
from contexts.preparation.application.get_template_service import (
    GetTemplateInput,
    GetTemplateService,
)
from contexts.preparation.application.list_templates_service import (
    ListTemplatesInput,
    ListTemplatesService,
)
from contexts.preparation.application.save_template_service import (
    SaveTemplateInput,
    SaveTemplateService,
)
from contexts.preparation.application.send_consultation_request_service import (
    SendConsultationRequestInput,
    SendConsultationRequestService,
)
from contexts.preparation.domain.value_objects import ScheduleGroupId, TemplateId
from contexts.preparation.presentation.dependencies import (
    get_create_schedule_group_from_past_service,
    get_create_schedule_group_from_template_service,
    get_create_schedule_group_service,
    get_create_schedule_service,
    get_get_template_service,
    get_list_templates_service,
    get_save_template_service,
    get_send_consultation_request_service,
)
from contexts.preparation.presentation.schemas import (
    CreateScheduleGroupFromPastRequest,
    CreateScheduleGroupFromPastResponse,
    CreateScheduleGroupFromTemplateRequest,
    CreateScheduleGroupFromTemplateResponse,
    CreateScheduleGroupRequest,
    CreateScheduleGroupResponse,
    CreateScheduleRequest,
    CreateScheduleResponse,
    GetTemplateResponse,
    ListTemplatesResponse,
    SaveTemplateRequest,
    SaveTemplateResponse,
    SendConsultationRequestRequest,
    SendConsultationRequestResponse,
    TemplateListItemSchema,
)
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

router = APIRouter()


# ---------------------------------------------------------------------------
# ScheduleGroup endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/schedule-groups",
    response_model=CreateScheduleGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule_group(
    body: CreateScheduleGroupRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        CreateScheduleGroupService, Depends(get_create_schedule_group_service)
    ],
) -> CreateScheduleGroupResponse:
    """Create a new ScheduleGroup with schedules for multiple counterparts."""
    input_dto = CreateScheduleGroupInput(
        organizer_id=current_user_id,
        title=body.title,
        counterpart_schedules=[
            CounterpartSchedule(
                counterpart_id=UserId(value=cs.counterpart_id),
                scheduled_at=cs.scheduled_at,
            )
            for cs in body.counterpart_schedules
        ],
        agenda_topics=body.agenda_topics,
        template_id=str(body.template_id) if body.template_id else None,
    )
    output = await service.execute(input_dto)
    return CreateScheduleGroupResponse(
        schedule_group_id=output.schedule_group_id.value,
    )


@router.post(
    "/schedule-groups/from-template",
    response_model=CreateScheduleGroupFromTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule_group_from_template(
    body: CreateScheduleGroupFromTemplateRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        CreateScheduleGroupFromTemplateService,
        Depends(get_create_schedule_group_from_template_service),
    ],
) -> CreateScheduleGroupFromTemplateResponse:
    """Create a new ScheduleGroup from a saved template."""
    input_dto = CreateScheduleGroupFromTemplateInput(
        organizer_id=current_user_id,
        template_id=TemplateId(value=body.template_id),
        title=body.title,
        counterpart_schedules=[
            TemplateCounterpartSchedule(
                counterpart_id=UserId(value=cs.counterpart_id),
                scheduled_at=cs.scheduled_at,
            )
            for cs in body.counterpart_schedules
        ],
    )
    output = await service.execute(input_dto)
    return CreateScheduleGroupFromTemplateResponse(
        schedule_group_id=output.schedule_group_id.value,
    )


@router.post(
    "/schedule-groups/from-past",
    response_model=CreateScheduleGroupFromPastResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule_group_from_past(
    body: CreateScheduleGroupFromPastRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        CreateScheduleGroupFromPastService,
        Depends(get_create_schedule_group_from_past_service),
    ],
) -> CreateScheduleGroupFromPastResponse:
    """Create a new ScheduleGroup by copying from a past group."""
    input_dto = CreateScheduleGroupFromPastInput(
        organizer_id=current_user_id,
        source_schedule_group_id=ScheduleGroupId(
            value=body.source_schedule_group_id,
        ),
        title=body.title,
        counterpart_schedules=[
            PastCounterpartSchedule(
                counterpart_id=UserId(value=cs.counterpart_id),
                scheduled_at=cs.scheduled_at,
            )
            for cs in body.counterpart_schedules
        ],
    )
    output = await service.execute(input_dto)
    return CreateScheduleGroupFromPastResponse(
        schedule_group_id=output.schedule_group_id.value,
    )


# ---------------------------------------------------------------------------
# Schedule endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/schedules",
    response_model=CreateScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    body: CreateScheduleRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[CreateScheduleService, Depends(get_create_schedule_service)],
) -> CreateScheduleResponse:
    """Create a single individual schedule."""
    input_dto = CreateScheduleInput(
        organizer_id=current_user_id,
        counterpart_id=UserId(value=body.counterpart_id),
        scheduled_at=body.scheduled_at,
        title=body.title,
    )
    output = await service.execute(input_dto)
    return CreateScheduleResponse(schedule_id=output.schedule_id.value)


@router.post(
    "/schedules/consultation-request",
    response_model=SendConsultationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_consultation_request(
    body: SendConsultationRequestRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        SendConsultationRequestService,
        Depends(get_send_consultation_request_service),
    ],
) -> SendConsultationRequestResponse:
    """Send an ad-hoc consultation request (counterpart to organizer)."""
    input_dto = SendConsultationRequestInput(
        organizer_id=UserId(value=body.organizer_id),
        counterpart_id=current_user_id,
        scheduled_at=body.scheduled_at,
        title=body.title,
        agenda_topics=body.agenda_topics,
        actor_id=current_user_id,
    )
    output = await service.execute(input_dto)
    return SendConsultationRequestResponse(schedule_id=output.schedule_id.value)


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=ListTemplatesResponse,
)
async def list_templates(
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[ListTemplatesService, Depends(get_list_templates_service)],
) -> ListTemplatesResponse:
    """List all templates owned by the current user."""
    input_dto = ListTemplatesInput(actor_id=current_user_id)
    output = await service.execute(input_dto)
    return ListTemplatesResponse(
        templates=[
            TemplateListItemSchema(
                template_id=t.template_id.value,
                name=t.name,
                default_counterpart_ids=[
                    uid.value for uid in t.default_counterpart_ids
                ],
                agenda_topics=t.agenda_topics,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in output.templates
        ],
    )


@router.get(
    "/templates/{template_id}",
    response_model=GetTemplateResponse,
)
async def get_template(
    template_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[GetTemplateService, Depends(get_get_template_service)],
) -> GetTemplateResponse:
    """Get a template by ID."""
    input_dto = GetTemplateInput(
        template_id=TemplateId(value=template_id),
        actor_id=current_user_id,
    )
    output = await service.execute(input_dto)
    return GetTemplateResponse(
        template_id=output.template_id.value,
        organizer_id=output.organizer_id.value,
        name=output.name,
        default_counterpart_ids=[uid.value for uid in output.default_counterpart_ids],
        agenda_topics=output.agenda_topics,
        created_at=output.created_at,
        updated_at=output.updated_at,
    )


@router.post(
    "/templates",
    response_model=SaveTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_template(
    body: SaveTemplateRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[SaveTemplateService, Depends(get_save_template_service)],
) -> SaveTemplateResponse:
    """Save a new template for reuse."""
    input_dto = SaveTemplateInput(
        organizer_id=current_user_id,
        name=body.name,
        default_counterpart_ids=[
            UserId(value=uid) for uid in body.default_counterpart_ids
        ],
        agenda_topics=body.agenda_topics,
    )
    output = await service.execute(input_dto)
    return SaveTemplateResponse(template_id=output.template_id.value)
