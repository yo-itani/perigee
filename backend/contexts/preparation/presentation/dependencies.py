"""DI providers for the Preparation context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_event_dispatcher, get_session, get_unit_of_work
from contexts.preparation.application.create_schedule_group_from_past_use_case import (
    CreateScheduleGroupFromPastUseCase,
)
from contexts.preparation.application.create_schedule_group_from_template_use_case import (  # noqa: E501
    CreateScheduleGroupFromTemplateUseCase,
)
from contexts.preparation.application.create_schedule_group_use_case import (
    CreateScheduleGroupUseCase,
)
from contexts.preparation.application.create_schedule_use_case import (
    CreateScheduleUseCase,
)
from contexts.preparation.application.get_template_query_service import (
    GetTemplateQueryService,
)
from contexts.preparation.application.list_templates_query_service import (
    ListTemplatesQueryService,
)
from contexts.preparation.application.save_template_use_case import (
    SaveTemplateUseCase,
)
from contexts.preparation.application.send_consultation_request_use_case import (
    SendConsultationRequestUseCase,
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
    from contexts.preparation.application.accept_consultation_request_use_case import (
        AcceptConsultationRequestUseCase,
    )
    from contexts.preparation.application.add_agenda_comment_use_case import (
        AddAgendaCommentUseCase,
    )
    from contexts.preparation.application.add_agenda_use_case import (
        AddAgendaUseCase,
    )
    from contexts.preparation.application.cancel_schedule_use_case import (
        CancelScheduleUseCase,
    )
    from contexts.preparation.application.delete_agenda_use_case import (
        DeleteAgendaUseCase,
    )
    from contexts.preparation.application.get_schedule_detail_query_service import (
        GetScheduleDetailQueryService,
    )
    from contexts.preparation.application.list_schedule_agendas_query_service import (
        ListScheduleAgendasQueryService,
    )
    from contexts.preparation.application.list_upcoming_schedules_query_service import (
        ListUpcomingSchedulesQueryService,
    )
    from contexts.preparation.application.reject_consultation_request_use_case import (
        RejectConsultationRequestUseCase,
    )
    from contexts.preparation.application.rename_schedule_use_case import (
        RenameScheduleUseCase,
    )
    from contexts.preparation.application.reschedule_use_case import (
        RescheduleUseCase,
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


def get_create_schedule_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleUseCase:
    """Provide a CreateScheduleUseCase with all dependencies injected."""
    return CreateScheduleUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupUseCase:
    """Provide a CreateScheduleGroupUseCase with all dependencies injected."""
    return CreateScheduleGroupUseCase(
        uow=uow,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_from_template_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupFromTemplateUseCase:
    """Provide a CreateScheduleGroupFromTemplateUseCase."""
    return CreateScheduleGroupFromTemplateUseCase(
        uow=uow,
        template_repo=template_repo,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_create_schedule_group_from_past_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_group_repo: Annotated[
        ScheduleGroupRepository, Depends(get_schedule_group_repository)
    ],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CreateScheduleGroupFromPastUseCase:
    """Provide a CreateScheduleGroupFromPastUseCase."""
    return CreateScheduleGroupFromPastUseCase(
        uow=uow,
        schedule_group_repo=schedule_group_repo,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_send_consultation_request_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SendConsultationRequestUseCase:
    """Provide a SendConsultationRequestUseCase."""
    return SendConsultationRequestUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_list_templates_query_service(
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
) -> ListTemplatesQueryService:
    """Provide a ListTemplatesQueryService."""
    return ListTemplatesQueryService(template_repo=template_repo)


def get_get_template_query_service(
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
) -> GetTemplateQueryService:
    """Provide a GetTemplateQueryService."""
    return GetTemplateQueryService(template_repo=template_repo)


def get_save_template_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    template_repo: Annotated[TemplateRepository, Depends(get_template_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> SaveTemplateUseCase:
    """Provide a SaveTemplateUseCase."""
    return SaveTemplateUseCase(
        uow=uow,
        template_repo=template_repo,
        event_dispatcher=event_dispatcher,
    )


# ---------------------------------------------------------------------------
# Preparation screen service providers
# ---------------------------------------------------------------------------


def get_get_schedule_detail_query_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
) -> GetScheduleDetailQueryService:
    """Provide a GetScheduleDetailQueryService."""
    from contexts.preparation.application.get_schedule_detail_query_service import (
        GetScheduleDetailQueryService,
    )

    return GetScheduleDetailQueryService(schedule_repo=schedule_repo)


def get_list_schedule_agendas_query_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
) -> ListScheduleAgendasQueryService:
    """Provide a ListScheduleAgendasQueryService."""
    from contexts.preparation.application.list_schedule_agendas_query_service import (
        ListScheduleAgendasQueryService,
    )

    return ListScheduleAgendasQueryService(
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
    )


def get_list_upcoming_schedules_query_service(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
) -> ListUpcomingSchedulesQueryService:
    """Provide a ListUpcomingSchedulesQueryService."""
    from contexts.preparation.application.list_upcoming_schedules_query_service import (
        ListUpcomingSchedulesQueryService,
    )

    return ListUpcomingSchedulesQueryService(schedule_repo=schedule_repo)


def get_accept_consultation_request_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AcceptConsultationRequestUseCase:
    """Provide an AcceptConsultationRequestUseCase."""
    from contexts.preparation.application.accept_consultation_request_use_case import (
        AcceptConsultationRequestUseCase,
    )

    return AcceptConsultationRequestUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_reject_consultation_request_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RejectConsultationRequestUseCase:
    """Provide a RejectConsultationRequestUseCase."""
    from contexts.preparation.application.reject_consultation_request_use_case import (
        RejectConsultationRequestUseCase,
    )

    return RejectConsultationRequestUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_reschedule_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RescheduleUseCase:
    """Provide a RescheduleUseCase."""
    from contexts.preparation.application.reschedule_use_case import RescheduleUseCase

    return RescheduleUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_cancel_schedule_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> CancelScheduleUseCase:
    """Provide a CancelScheduleUseCase."""
    from contexts.preparation.application.cancel_schedule_use_case import (
        CancelScheduleUseCase,
    )

    return CancelScheduleUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_rename_schedule_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> RenameScheduleUseCase:
    """Provide a RenameScheduleUseCase."""
    from contexts.preparation.application.rename_schedule_use_case import (
        RenameScheduleUseCase,
    )

    return RenameScheduleUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        event_dispatcher=event_dispatcher,
    )


def get_add_agenda_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddAgendaUseCase:
    """Provide an AddAgendaUseCase."""
    from contexts.preparation.application.add_agenda_use_case import AddAgendaUseCase

    return AddAgendaUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_delete_agenda_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> DeleteAgendaUseCase:
    """Provide a DeleteAgendaUseCase."""
    from contexts.preparation.application.delete_agenda_use_case import (
        DeleteAgendaUseCase,
    )

    return DeleteAgendaUseCase(
        uow=uow,
        schedule_repo=schedule_repo,
        agenda_repo=agenda_repo,
        event_dispatcher=event_dispatcher,
    )


def get_add_agenda_comment_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    agenda_repo: Annotated[AgendaRepository, Depends(get_agenda_repository)],
    event_dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> AddAgendaCommentUseCase:
    """Provide an AddAgendaCommentUseCase."""
    from contexts.preparation.application.add_agenda_comment_use_case import (
        AddAgendaCommentUseCase,
    )

    return AddAgendaCommentUseCase(
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
