"""DI providers for the Preparation context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.preparation.application.create_schedule_group_from_past_service import (
    CreateScheduleGroupFromPastService,
)
from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    CreateScheduleGroupFromTemplateService,
)
from contexts.preparation.application.create_schedule_group_service import (
    CreateScheduleGroupService,
)
from contexts.preparation.application.create_schedule_service import (
    CreateScheduleService,
)
from contexts.preparation.application.get_template_service import (
    GetTemplateService,
)
from contexts.preparation.application.list_templates_service import (
    ListTemplatesService,
)
from contexts.preparation.application.save_template_service import (
    SaveTemplateService,
)
from contexts.preparation.application.send_consultation_request_service import (
    SendConsultationRequestService,
)
from contexts.preparation.domain.agenda_repository import AgendaRepository
from contexts.preparation.domain.schedule_group_repository import (
    ScheduleGroupRepository,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.template_repository import TemplateRepository
from contexts.preparation.infrastructure.sqlalchemy_agenda_repository import (
    SqlAlchemyAgendaRepository,
)
from contexts.preparation.infrastructure.sqlalchemy_schedule_group_repository import (
    SqlAlchemyScheduleGroupRepository,
)
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    SqlAlchemyScheduleRepository,
)
from contexts.preparation.infrastructure.sqlalchemy_template_repository import (
    SqlAlchemyTemplateRepository,
)
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher

if TYPE_CHECKING:
    from contexts.preparation.application.accept_consultation_request_service import (
        AcceptConsultationRequestService,
    )
    from contexts.preparation.application.add_agenda_comment_service import (
        AddAgendaCommentService,
    )
    from contexts.preparation.application.add_agenda_service import (
        AddAgendaService,
    )
    from contexts.preparation.application.cancel_schedule_service import (
        CancelScheduleService,
    )
    from contexts.preparation.application.delete_agenda_service import (
        DeleteAgendaService,
    )
    from contexts.preparation.application.get_schedule_detail_service import (
        GetScheduleDetailService,
    )
    from contexts.preparation.application.list_schedule_agendas_service import (
        ListScheduleAgendasService,
    )
    from contexts.preparation.application.list_upcoming_schedules_service import (
        ListUpcomingSchedulesService,
    )
    from contexts.preparation.application.reject_consultation_request_service import (
        RejectConsultationRequestService,
    )
    from contexts.preparation.application.rename_schedule_service import (
        RenameScheduleService,
    )
    from contexts.preparation.application.reschedule_service import (
        RescheduleService,
    )
    from contexts.record.application.get_last_session_summary import (
        GetLastSessionSummaryQueryService,
    )
    from contexts.record.application.list_all_pending_action_items import (
        ListAllPendingActionItemsQueryService,
    )
    from contexts.record.application.list_pending_action_items import (
        ListPendingActionItemsQueryService,
    )
    from contexts.record.domain.action_item_repository import ActionItemRepository
    from contexts.record.domain.record_repository import RecordRepository


def get_schedule_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScheduleRepository:
    """Provide a ScheduleRepository backed by the current DB session."""
    return SqlAlchemyScheduleRepository(session)


def get_schedule_group_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScheduleGroupRepository:
    """Provide a ScheduleGroupRepository backed by the current DB session."""
    return SqlAlchemyScheduleGroupRepository(session)


def get_template_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateRepository:
    """Provide a TemplateRepository backed by the current DB session."""
    return SqlAlchemyTemplateRepository(session)


def get_agenda_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgendaRepository:
    """Provide an AgendaRepository backed by the current DB session."""
    return SqlAlchemyAgendaRepository(session)


def _get_record_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecordRepository:
    """Provide a RecordRepository backed by the current DB session."""
    from contexts.record.infrastructure.sqlalchemy_record_repository import (
        SqlAlchemyRecordRepository,
    )

    return SqlAlchemyRecordRepository(session)


def _get_action_item_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionItemRepository:
    """Provide an ActionItemRepository backed by the current DB session."""
    from contexts.record.infrastructure.sqlalchemy_action_item_repository import (
        SqlAlchemyActionItemRepository,
    )

    return SqlAlchemyActionItemRepository(session)


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------


def get_create_schedule_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleService:
    """Provide a CreateScheduleService with all dependencies injected."""
    return CreateScheduleService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupService:
    """Provide a CreateScheduleGroupService with all dependencies injected."""
    return CreateScheduleGroupService(
        uow=uow,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_from_template_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupFromTemplateService:
    """Provide a CreateScheduleGroupFromTemplateService."""
    return CreateScheduleGroupFromTemplateService(
        uow=uow,
        template_repo=template_repo,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_from_past_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupFromPastService:
    """Provide a CreateScheduleGroupFromPastService."""
    return CreateScheduleGroupFromPastService(
        uow=uow,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_send_consultation_request_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SendConsultationRequestService:
    """Provide a SendConsultationRequestService."""
    return SendConsultationRequestService(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_list_templates_service(
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
) -> ListTemplatesService:
    """Provide a ListTemplatesService."""
    return ListTemplatesService(template_repo=template_repo)


def get_get_template_service(
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
) -> GetTemplateService:
    """Provide a GetTemplateService."""
    return GetTemplateService(template_repo=template_repo)


def get_save_template_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SaveTemplateService:
    """Provide a SaveTemplateService."""
    return SaveTemplateService(
        uow=uow,
        template_repo=template_repo,
        event_dispatcher=event_dispatcher,
    )


# ---------------------------------------------------------------------------
# Preparation screen service providers
# ---------------------------------------------------------------------------


def get_get_schedule_detail_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
) -> GetScheduleDetailService:
    """Provide a GetScheduleDetailService."""
    from contexts.preparation.application.get_schedule_detail_service import (
        GetScheduleDetailService,
    )

    return GetScheduleDetailService(schedule_repo=schedule_repo)


def get_list_schedule_agendas_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
) -> ListScheduleAgendasService:
    """Provide a ListScheduleAgendasService."""
    from contexts.preparation.application.list_schedule_agendas_service import (
        ListScheduleAgendasService,
    )

    return ListScheduleAgendasService(
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
    )


def get_list_upcoming_schedules_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
) -> ListUpcomingSchedulesService:
    """Provide a ListUpcomingSchedulesService."""
    from contexts.preparation.application.list_upcoming_schedules_service import (
        ListUpcomingSchedulesService,
    )

    return ListUpcomingSchedulesService(schedule_repo=schedule_repo)


def get_accept_consultation_request_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AcceptConsultationRequestService:
    """Provide an AcceptConsultationRequestService."""
    from contexts.preparation.application.accept_consultation_request_service import (
        AcceptConsultationRequestService,
    )

    return AcceptConsultationRequestService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_reject_consultation_request_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RejectConsultationRequestService:
    """Provide a RejectConsultationRequestService."""
    from contexts.preparation.application.reject_consultation_request_service import (
        RejectConsultationRequestService,
    )

    return RejectConsultationRequestService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_reschedule_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RescheduleService:
    """Provide a RescheduleService."""
    from contexts.preparation.application.reschedule_service import RescheduleService

    return RescheduleService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_cancel_schedule_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CancelScheduleService:
    """Provide a CancelScheduleService."""
    from contexts.preparation.application.cancel_schedule_service import (
        CancelScheduleService,
    )

    return CancelScheduleService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_rename_schedule_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RenameScheduleService:
    """Provide a RenameScheduleService."""
    from contexts.preparation.application.rename_schedule_service import (
        RenameScheduleService,
    )

    return RenameScheduleService(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_add_agenda_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddAgendaService:
    """Provide an AddAgendaService."""
    from contexts.preparation.application.add_agenda_service import AddAgendaService

    return AddAgendaService(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_delete_agenda_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> DeleteAgendaService:
    """Provide a DeleteAgendaService."""
    from contexts.preparation.application.delete_agenda_service import (
        DeleteAgendaService,
    )

    return DeleteAgendaService(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_add_agenda_comment_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddAgendaCommentService:
    """Provide an AddAgendaCommentService."""
    from contexts.preparation.application.add_agenda_comment_service import (
        AddAgendaCommentService,
    )

    return AddAgendaCommentService(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_list_pending_action_items_service(
    record_repo: Annotated[RecordRepository, Depends(_get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(_get_action_item_repository)
    ],
) -> ListPendingActionItemsQueryService:
    """Provide a ListPendingActionItemsQueryService."""
    from contexts.record.application.list_pending_action_items import (
        ListPendingActionItemsQueryService,
    )

    return ListPendingActionItemsQueryService(
        action_item_repository=action_item_repo,
        record_repository=record_repo,
    )


def get_list_all_pending_action_items_service(
    record_repo: Annotated[RecordRepository, Depends(_get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(_get_action_item_repository)
    ],
) -> ListAllPendingActionItemsQueryService:
    """Provide a ListAllPendingActionItemsQueryService."""
    from contexts.record.application.list_all_pending_action_items import (
        ListAllPendingActionItemsQueryService,
    )

    return ListAllPendingActionItemsQueryService(
        action_item_repository=action_item_repo,
        record_repository=record_repo,
    )


def get_get_last_session_summary_service(
    record_repo: Annotated[RecordRepository, Depends(_get_record_repository)],
    action_item_repo: Annotated[
        ActionItemRepository, Depends(_get_action_item_repository)
    ],
) -> GetLastSessionSummaryQueryService:
    """Provide a GetLastSessionSummaryQueryService."""
    from contexts.record.application.get_last_session_summary import (
        GetLastSessionSummaryQueryService,
    )

    return GetLastSessionSummaryQueryService(
        record_repository=record_repo,
        action_item_repository=action_item_repo,
    )
