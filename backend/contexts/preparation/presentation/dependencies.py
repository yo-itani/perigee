"""DI providers for the Preparation context."""

from __future__ import annotations

from typing import Annotated

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
