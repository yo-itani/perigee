"""FastAPI router for the Preparation context (setup + preparation screen)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contexts.preparation.application.accept_consultation_request_service import (
    AcceptConsultationRequestInput,
    AcceptConsultationRequestService,
)
from contexts.preparation.application.add_agenda_comment_service import (
    AddAgendaCommentInput,
    AddAgendaCommentService,
)
from contexts.preparation.application.add_agenda_service import (
    AddAgendaInput,
    AddAgendaService,
)
from contexts.preparation.application.cancel_schedule_service import (
    CancelScheduleInput,
    CancelScheduleService,
)
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
from contexts.preparation.application.delete_agenda_service import (
    DeleteAgendaInput,
    DeleteAgendaService,
)
from contexts.preparation.application.get_schedule_detail_service import (
    GetScheduleDetailInput,
    GetScheduleDetailService,
)
from contexts.preparation.application.get_template_service import (
    GetTemplateInput,
    GetTemplateService,
)
from contexts.preparation.application.list_schedule_agendas_service import (
    ListScheduleAgendasInput,
    ListScheduleAgendasService,
)
from contexts.preparation.application.list_templates_service import (
    ListTemplatesInput,
    ListTemplatesService,
)
from contexts.preparation.application.list_upcoming_schedules_service import (
    ListUpcomingSchedulesInput,
    ListUpcomingSchedulesService,
)
from contexts.preparation.application.reject_consultation_request_service import (
    RejectConsultationRequestInput,
    RejectConsultationRequestService,
)
from contexts.preparation.application.rename_schedule_service import (
    RenameScheduleInput,
    RenameScheduleService,
)
from contexts.preparation.application.reschedule_service import (
    RescheduleInput,
    RescheduleService,
)
from contexts.preparation.application.save_template_service import (
    SaveTemplateInput,
    SaveTemplateService,
)
from contexts.preparation.application.send_consultation_request_service import (
    SendConsultationRequestInput,
    SendConsultationRequestService,
)
from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
from contexts.preparation.presentation.dependencies import (
    get_accept_consultation_request_service,
    get_add_agenda_comment_service,
    get_add_agenda_service,
    get_cancel_schedule_service,
    get_create_schedule_group_from_past_service,
    get_create_schedule_group_from_template_service,
    get_create_schedule_group_service,
    get_create_schedule_service,
    get_delete_agenda_service,
    get_get_last_session_summary_service,
    get_get_schedule_detail_service,
    get_get_template_service,
    get_list_pending_action_items_service,
    get_list_schedule_agendas_service,
    get_list_templates_service,
    get_list_upcoming_schedules_service,
    get_reject_consultation_request_service,
    get_rename_schedule_service,
    get_reschedule_service,
    get_save_template_service,
    get_send_consultation_request_service,
)
from contexts.preparation.presentation.schemas import (
    ActionItemSummarySchema,
    AddAgendaCommentRequest,
    AddAgendaCommentResponse,
    AddAgendaRequest,
    AddAgendaResponse,
    AgendaCommentSchema,
    AgendaItemSchema,
    CreateScheduleGroupFromPastRequest,
    CreateScheduleGroupFromPastResponse,
    CreateScheduleGroupFromTemplateRequest,
    CreateScheduleGroupFromTemplateResponse,
    CreateScheduleGroupRequest,
    CreateScheduleGroupResponse,
    CreateScheduleRequest,
    CreateScheduleResponse,
    GetLastSessionSummaryResponse,
    GetScheduleDetailResponse,
    GetTemplateResponse,
    ListPendingActionItemsResponse,
    ListScheduleAgendasResponse,
    ListTemplatesResponse,
    ListUpcomingSchedulesResponse,
    PendingActionItemSchema,
    RenameScheduleRequest,
    RescheduleRequest,
    SaveTemplateRequest,
    SaveTemplateResponse,
    SendConsultationRequestRequest,
    SendConsultationRequestResponse,
    TemplateListItemSchema,
    UpcomingScheduleItemSchema,
)
from contexts.record.application.get_last_session_summary import (
    GetLastSessionSummaryInput,
    GetLastSessionSummaryService,
)
from contexts.record.application.list_pending_action_items import (
    ListPendingActionItemsInput,
    ListPendingActionItemsService,
)
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

router = APIRouter()


# -- ScheduleGroup endpoints ------------------------------------------------


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
    output = await service.execute(
        CreateScheduleGroupInput(
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
    )
    return CreateScheduleGroupResponse(schedule_group_id=output.schedule_group_id.value)


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
    output = await service.execute(
        CreateScheduleGroupFromTemplateInput(
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
    )
    return CreateScheduleGroupFromTemplateResponse(
        schedule_group_id=output.schedule_group_id.value
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
    output = await service.execute(
        CreateScheduleGroupFromPastInput(
            organizer_id=current_user_id,
            source_schedule_group_id=ScheduleGroupId(
                value=body.source_schedule_group_id
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
    )
    return CreateScheduleGroupFromPastResponse(
        schedule_group_id=output.schedule_group_id.value
    )


# -- Schedule creation endpoints ---------------------------------------------


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
    output = await service.execute(
        CreateScheduleInput(
            organizer_id=current_user_id,
            counterpart_id=UserId(value=body.counterpart_id),
            scheduled_at=body.scheduled_at,
            title=body.title,
        )
    )
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
        SendConsultationRequestService, Depends(get_send_consultation_request_service)
    ],
) -> SendConsultationRequestResponse:
    output = await service.execute(
        SendConsultationRequestInput(
            organizer_id=UserId(value=body.organizer_id),
            counterpart_id=current_user_id,
            scheduled_at=body.scheduled_at,
            title=body.title,
            agenda_topics=body.agenda_topics,
            actor_id=current_user_id,
        )
    )
    return SendConsultationRequestResponse(schedule_id=output.schedule_id.value)


@router.get("/schedules/upcoming", response_model=ListUpcomingSchedulesResponse)
async def list_upcoming_schedules(
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        ListUpcomingSchedulesService, Depends(get_list_upcoming_schedules_service)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListUpcomingSchedulesResponse:
    output = await service.execute(
        ListUpcomingSchedulesInput(actor_id=current_user_id, limit=limit)
    )
    return ListUpcomingSchedulesResponse(
        schedules=[
            UpcomingScheduleItemSchema(
                schedule_id=s.schedule_id.value,
                organizer_id=s.organizer_id.value,
                counterpart_id=s.counterpart_id.value,
                scheduled_at=s.scheduled_at,
                status=s.status.value,
                title=s.title,
                schedule_group_id=s.schedule_group_id.value
                if s.schedule_group_id
                else None,
            )
            for s in output.schedules
        ]
    )


# -- Schedule detail + operations (preparation screen) -----------------------


@router.get("/schedules/{schedule_id}", response_model=GetScheduleDetailResponse)
async def get_schedule_detail(
    schedule_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        GetScheduleDetailService, Depends(get_get_schedule_detail_service)
    ],
) -> GetScheduleDetailResponse:
    output = await service.execute(
        GetScheduleDetailInput(
            schedule_id=ScheduleId(value=schedule_id), actor_id=current_user_id
        )
    )
    return GetScheduleDetailResponse(
        schedule_id=output.schedule_id.value,
        organizer_id=output.organizer_id.value,
        counterpart_id=output.counterpart_id.value,
        title=output.title,
        scheduled_at=output.scheduled_at,
        status=output.status.value,
        schedule_group_id=output.schedule_group_id.value
        if output.schedule_group_id
        else None,
        created_at=output.created_at,
        updated_at=output.updated_at,
    )


@router.get(
    "/schedules/{schedule_id}/agendas", response_model=ListScheduleAgendasResponse
)
async def list_schedule_agendas(
    schedule_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        ListScheduleAgendasService, Depends(get_list_schedule_agendas_service)
    ],
) -> ListScheduleAgendasResponse:
    output = await service.execute(
        ListScheduleAgendasInput(
            schedule_id=ScheduleId(value=schedule_id), actor_id=current_user_id
        )
    )
    return ListScheduleAgendasResponse(
        agendas=[
            AgendaItemSchema(
                agenda_id=a.agenda_id.value,
                topic=a.topic,
                added_by=a.added_by.value,
                added_by_tag=a.added_by_tag.value,
                comments=[
                    AgendaCommentSchema(
                        comment_id=c.comment_id.value,
                        author_id=c.author_id.value,
                        body=c.body,
                        created_at=c.created_at,
                    )
                    for c in a.comments
                ],
                created_at=a.created_at,
            )
            for a in output.agendas
        ]
    )


@router.post("/schedules/{schedule_id}/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_schedule(
    schedule_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        AcceptConsultationRequestService,
        Depends(get_accept_consultation_request_service),
    ],
) -> None:
    await service.execute(
        AcceptConsultationRequestInput(
            schedule_id=ScheduleId(value=schedule_id), actor_id=current_user_id
        )
    )


@router.post("/schedules/{schedule_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_schedule(
    schedule_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        RejectConsultationRequestService,
        Depends(get_reject_consultation_request_service),
    ],
) -> None:
    await service.execute(
        RejectConsultationRequestInput(
            schedule_id=ScheduleId(value=schedule_id), actor_id=current_user_id
        )
    )


@router.post(
    "/schedules/{schedule_id}/reschedule", status_code=status.HTTP_204_NO_CONTENT
)
async def reschedule(
    schedule_id: UUID,
    body: RescheduleRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[RescheduleService, Depends(get_reschedule_service)],
) -> None:
    await service.execute(
        RescheduleInput(
            schedule_id=ScheduleId(value=schedule_id),
            actor_id=current_user_id,
            new_scheduled_at=body.new_scheduled_at,
        )
    )


@router.post("/schedules/{schedule_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_schedule(
    schedule_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[CancelScheduleService, Depends(get_cancel_schedule_service)],
) -> None:
    await service.execute(
        CancelScheduleInput(
            schedule_id=ScheduleId(value=schedule_id), actor_id=current_user_id
        )
    )


@router.put("/schedules/{schedule_id}/title", status_code=status.HTTP_204_NO_CONTENT)
async def rename_schedule(
    schedule_id: UUID,
    body: RenameScheduleRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[RenameScheduleService, Depends(get_rename_schedule_service)],
) -> None:
    await service.execute(
        RenameScheduleInput(
            schedule_id=ScheduleId(value=schedule_id),
            new_title=body.title,
            actor_id=current_user_id,
        )
    )


# -- Agenda endpoints (preparation screen) -----------------------------------


@router.post(
    "/schedules/{schedule_id}/agendas",
    response_model=AddAgendaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_agenda(
    schedule_id: UUID,
    body: AddAgendaRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[AddAgendaService, Depends(get_add_agenda_service)],
) -> AddAgendaResponse:
    output = await service.execute(
        AddAgendaInput(
            schedule_id=ScheduleId(value=schedule_id),
            topic=body.topic,
            actor_id=current_user_id,
        )
    )
    return AddAgendaResponse(agenda_id=output.agenda_id.value)


@router.delete(
    "/schedules/{schedule_id}/agendas/{agenda_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agenda(
    schedule_id: UUID,
    agenda_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[DeleteAgendaService, Depends(get_delete_agenda_service)],
) -> None:
    await service.execute(
        DeleteAgendaInput(
            schedule_id=ScheduleId(value=schedule_id),
            agenda_id=AgendaId(value=agenda_id),
            actor_id=current_user_id,
        )
    )


# -- Agenda comment endpoint -------------------------------------------------


@router.post(
    "/agendas/{agenda_id}/comments",
    response_model=AddAgendaCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_agenda_comment(
    agenda_id: UUID,
    body: AddAgendaCommentRequest,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        AddAgendaCommentService, Depends(get_add_agenda_comment_service)
    ],
) -> AddAgendaCommentResponse:
    output = await service.execute(
        AddAgendaCommentInput(
            agenda_id=AgendaId(value=agenda_id),
            body=body.body,
            actor_id=current_user_id,
        )
    )
    return AddAgendaCommentResponse(comment_id=output.comment_id.value)


# -- Action items (cross-context read) --------------------------------------


@router.get(
    "/action-items/pending/{counterpart_id}",
    response_model=ListPendingActionItemsResponse,
)
async def list_pending_action_items(
    counterpart_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        ListPendingActionItemsService, Depends(get_list_pending_action_items_service)
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ListPendingActionItemsResponse:
    output = await service.execute(
        ListPendingActionItemsInput(
            actor_id=current_user_id,
            counterpart_id=UserId(value=counterpart_id),
            limit=limit,
        )
    )
    return ListPendingActionItemsResponse(
        items=[
            PendingActionItemSchema(
                action_item_id=item.action_item_id.value,
                content=item.content,
                created_at=item.created_at,
                record_id=item.record_id.value,
                organizer_id=item.organizer_id.value,
                conducted_at=item.conducted_at,
            )
            for item in output.items
        ]
    )


# -- Records (cross-context read) -------------------------------------------


@router.get(
    "/records/last-summary", response_model=GetLastSessionSummaryResponse | None
)
async def get_last_session_summary(
    organizer_id: Annotated[UUID, Query()],
    counterpart_id: Annotated[UUID, Query()],
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[
        GetLastSessionSummaryService, Depends(get_get_last_session_summary_service)
    ],
) -> GetLastSessionSummaryResponse | None:
    output = await service.execute(
        GetLastSessionSummaryInput(
            actor_id=current_user_id,
            organizer_id=UserId(value=organizer_id),
            counterpart_id=UserId(value=counterpart_id),
        )
    )
    if output is None:
        return None
    return GetLastSessionSummaryResponse(
        record_id=output.record_id.value,
        conducted_at=output.conducted_at,
        memo_excerpt=output.memo_excerpt,
        action_items=[
            ActionItemSummarySchema(
                action_item_id=ai.action_item_id.value,
                content=ai.content,
                is_completed=ai.is_completed,
                created_at=ai.created_at,
            )
            for ai in output.action_items
        ],
    )


# -- Template endpoints ------------------------------------------------------


@router.get("/templates", response_model=ListTemplatesResponse)
async def list_templates(
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[ListTemplatesService, Depends(get_list_templates_service)],
) -> ListTemplatesResponse:
    output = await service.execute(ListTemplatesInput(actor_id=current_user_id))
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
        ]
    )


@router.get("/templates/{template_id}", response_model=GetTemplateResponse)
async def get_template(
    template_id: UUID,
    current_user_id: Annotated[UserId, Depends(get_current_user_id)],
    service: Annotated[GetTemplateService, Depends(get_get_template_service)],
) -> GetTemplateResponse:
    output = await service.execute(
        GetTemplateInput(
            template_id=TemplateId(value=template_id), actor_id=current_user_id
        )
    )
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
    output = await service.execute(
        SaveTemplateInput(
            organizer_id=current_user_id,
            name=body.name,
            default_counterpart_ids=[
                UserId(value=uid) for uid in body.default_counterpart_ids
            ],
            agenda_topics=body.agenda_topics,
        )
    )
    return SaveTemplateResponse(template_id=output.template_id.value)
