"""Centralized exception-to-HTTP-status mapping and handler registration."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

# --- Notification context: domain exceptions ---
from contexts.notification.domain.exceptions import (
    InvalidReminderMinutesError,
)
from contexts.notification.domain.exceptions import (
    UnauthorizedOperationError as NotificationUnauthorizedOperationError,
)

# --- Preparation context: application exceptions ---
from contexts.preparation.application.accept_consultation_request_service import (
    ScheduleNotFoundError as AcceptConsultationScheduleNotFoundError,
)
from contexts.preparation.application.add_agenda_comment_service import (
    AgendaNotFoundError as AgendaCommentAgendaNotFoundError,
)
from contexts.preparation.application.add_agenda_comment_service import (
    ScheduleNotFoundError as AgendaCommentScheduleNotFoundError,
)
from contexts.preparation.application.add_agenda_comment_service import (
    UnauthorizedAgendaCommentError,
)
from contexts.preparation.application.add_agenda_service import (
    ScheduleNotFoundError as AddAgendaScheduleNotFoundError,
)
from contexts.preparation.application.add_agenda_service import (
    UnauthorizedAgendaOperationError as AddAgendaUnauthorizedError,
)
from contexts.preparation.application.add_agenda_to_group_service import (
    ScheduleGroupNotFoundError as AddAgendaToGroupScheduleGroupNotFoundError,
)
from contexts.preparation.application.cancel_schedule_group_service import (
    ScheduleGroupNotFoundError as CancelGroupScheduleGroupNotFoundError,
)
from contexts.preparation.application.cancel_schedule_service import (
    ScheduleNotFoundError as CancelScheduleNotFoundError,
)
from contexts.preparation.application.create_schedule_group_from_past_service import (
    SourceScheduleGroupNotFoundError,
    UnauthorizedCopyError,
)
from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    TemplateNotFoundError as CreateFromTemplateTemplateNotFoundError,
)
from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    UnauthorizedTemplateUseError,
)
from contexts.preparation.application.delete_agenda_service import (
    AgendaNotFoundError as DeleteAgendaNotFoundError,
)
from contexts.preparation.application.delete_agenda_service import (
    ScheduleNotFoundError as DeleteAgendaScheduleNotFoundError,
)
from contexts.preparation.application.delete_agenda_service import (
    UnauthorizedAgendaOperationError as DeleteAgendaUnauthorizedError,
)
from contexts.preparation.application.get_template_service import (
    TemplateNotFoundError as GetTemplateNotFoundError,
)
from contexts.preparation.application.get_template_service import (
    UnauthorizedTemplateAccessError,
)
from contexts.preparation.application.reject_consultation_request_service import (
    ScheduleNotFoundError as RejectConsultationScheduleNotFoundError,
)
from contexts.preparation.application.remove_agenda_from_group_service import (
    ScheduleGroupNotFoundError as RemoveAgendaFromGroupScheduleGroupNotFoundError,
)
from contexts.preparation.application.rename_schedule_group_service import (
    ScheduleGroupNotFoundError as RenameGroupScheduleGroupNotFoundError,
)
from contexts.preparation.application.rename_schedule_service import (
    ScheduleNotFoundError as RenameScheduleNotFoundError,
)
from contexts.preparation.application.rename_schedule_service import (
    UnauthorizedRenameError,
)
from contexts.preparation.application.reschedule_service import (
    ScheduleNotFoundError as RescheduleScheduleNotFoundError,
)

# --- Preparation context: domain exceptions ---
from contexts.preparation.domain.exceptions import (
    AgendaEditNotAllowedError,
    InconsistentScheduleAgendasError,
    InconsistentSchedulesError,
    InvalidScheduleOperationError,
    InvalidScheduleTitleError,
    InvalidTemplateNameError,
    InvalidTopicError,
    NoPendingConfirmationRequestError,
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleGroupOperationError,
    UnauthorizedScheduleOperationError,
    UnauthorizedTemplateOperationError,
)
from contexts.preparation.domain.exceptions import (
    InvalidCommentBodyError as PreparationInvalidCommentBodyError,
)

# --- Record context: application exceptions ---
from contexts.record.application.add_action_item import (
    RecordNotFoundError as AddActionItemRecordNotFoundError,
)
from contexts.record.application.add_comment import (
    RecordNotFoundError as AddCommentRecordNotFoundError,
)
from contexts.record.application.complete_action_item import (
    ActionItemNotFoundError,
)
from contexts.record.application.confirm_agenda import (
    RecordNotFoundError as ConfirmAgendaRecordNotFoundError,
)
from contexts.record.application.create_post_hoc_record import (
    SameUserError,
)
from contexts.record.application.create_record_from_schedule import (
    ScheduleCancelledError,
)
from contexts.record.application.create_record_from_schedule import (
    ScheduleNotFoundError as CreateRecordScheduleNotFoundError,
)
from contexts.record.application.get_viewers import (
    RecordNotFoundError as GetViewersRecordNotFoundError,
)
from contexts.record.application.list_oneonone_history import (
    InvalidPaginationError,
)
from contexts.record.application.list_pending_action_items import (
    InvalidLimitError,
)
from contexts.record.application.publish_record import (
    RecordNotFoundError as PublishRecordNotFoundError,
)
from contexts.record.application.save_draft import (
    RecordNotFoundError as SaveDraftRecordNotFoundError,
)
from contexts.record.application.set_viewers import (
    RecordNotFoundError as SetViewersRecordNotFoundError,
)
from contexts.record.application.suggest_default_viewers import (
    RecordNotFoundError as SuggestViewersRecordNotFoundError,
)
from contexts.record.application.update_memo import (
    RecordNotFoundError as UpdateMemoRecordNotFoundError,
)

# --- Record context: domain exceptions ---
from contexts.record.domain.exceptions import (
    ActionItemAlreadyCompletedError,
    AgendaAlreadyConfirmedError,
    CommentAlreadyExistsError,
    InvalidActionItemTitleError,
    InvalidMemoError,
    RecordAlreadyPublishedError,
    RecordNotPublishedError,
)
from contexts.record.domain.exceptions import (
    InvalidCommentBodyError as RecordInvalidCommentBodyError,
)
from contexts.record.domain.exceptions import (
    UnauthorizedOperationError as RecordUnauthorizedOperationError,
)

# --- Workspace context: application exceptions ---
from contexts.workspace.application.add_member_service import (
    WorkspaceNotFoundError as AddMemberWorkspaceNotFoundError,
)
from contexts.workspace.application.change_member_role_service import (
    WorkspaceNotFoundError as ChangeMemberRoleWorkspaceNotFoundError,
)
from contexts.workspace.application.change_workspace_parent_service import (
    ParentWorkspaceNotFoundError as ChangeParentParentNotFoundError,
)
from contexts.workspace.application.change_workspace_parent_service import (
    WorkspaceNotFoundError as ChangeParentWorkspaceNotFoundError,
)
from contexts.workspace.application.create_workspace_service import (
    ParentWorkspaceNotFoundError as CreateWorkspaceParentNotFoundError,
)
from contexts.workspace.application.remove_member_service import (
    WorkspaceNotFoundError as RemoveMemberWorkspaceNotFoundError,
)
from contexts.workspace.application.rename_workspace_service import (
    WorkspaceNotFoundError as RenameWorkspaceNotFoundError,
)

# --- Workspace context: domain exceptions ---
from contexts.workspace.domain.exceptions import (
    CircularHierarchyError,
    DuplicateMembershipError,
    InvalidWorkspaceNameError,
    MembershipNotFoundError,
)

EXCEPTION_STATUS_MAP: dict[type[Exception], int] = {
    # -------------------------------------------------------
    # 403 Forbidden -- authorization / permission errors
    # -------------------------------------------------------
    RecordUnauthorizedOperationError: 403,
    NotificationUnauthorizedOperationError: 403,
    UnauthorizedScheduleOperationError: 403,
    UnauthorizedScheduleGroupOperationError: 403,
    UnauthorizedTemplateOperationError: 403,
    UnauthorizedCopyError: 403,
    UnauthorizedTemplateUseError: 403,
    UnauthorizedTemplateAccessError: 403,
    UnauthorizedAgendaCommentError: 403,
    AddAgendaUnauthorizedError: 403,
    DeleteAgendaUnauthorizedError: 403,
    UnauthorizedRenameError: 403,
    # -------------------------------------------------------
    # 404 Not Found
    # -------------------------------------------------------
    # Preparation -- Schedule
    CancelScheduleNotFoundError: 404,
    RescheduleScheduleNotFoundError: 404,
    RejectConsultationScheduleNotFoundError: 404,
    AcceptConsultationScheduleNotFoundError: 404,
    AddAgendaScheduleNotFoundError: 404,
    AgendaCommentScheduleNotFoundError: 404,
    DeleteAgendaScheduleNotFoundError: 404,
    RenameScheduleNotFoundError: 404,
    # Preparation -- ScheduleGroup
    AddAgendaToGroupScheduleGroupNotFoundError: 404,
    RemoveAgendaFromGroupScheduleGroupNotFoundError: 404,
    RenameGroupScheduleGroupNotFoundError: 404,
    CancelGroupScheduleGroupNotFoundError: 404,
    SourceScheduleGroupNotFoundError: 404,
    # Preparation -- Template
    GetTemplateNotFoundError: 404,
    CreateFromTemplateTemplateNotFoundError: 404,
    # Preparation -- Agenda
    DeleteAgendaNotFoundError: 404,
    AgendaCommentAgendaNotFoundError: 404,
    # Record -- Record
    AddActionItemRecordNotFoundError: 404,
    AddCommentRecordNotFoundError: 404,
    ConfirmAgendaRecordNotFoundError: 404,
    GetViewersRecordNotFoundError: 404,
    PublishRecordNotFoundError: 404,
    SaveDraftRecordNotFoundError: 404,
    SetViewersRecordNotFoundError: 404,
    SuggestViewersRecordNotFoundError: 404,
    UpdateMemoRecordNotFoundError: 404,
    CreateRecordScheduleNotFoundError: 404,
    # Record -- ActionItem
    ActionItemNotFoundError: 404,
    # Workspace
    AddMemberWorkspaceNotFoundError: 404,
    ChangeMemberRoleWorkspaceNotFoundError: 404,
    ChangeParentWorkspaceNotFoundError: 404,
    ChangeParentParentNotFoundError: 404,
    CreateWorkspaceParentNotFoundError: 404,
    RemoveMemberWorkspaceNotFoundError: 404,
    RenameWorkspaceNotFoundError: 404,
    MembershipNotFoundError: 404,
    # -------------------------------------------------------
    # 409 Conflict -- state violation
    # -------------------------------------------------------
    ScheduleAlreadyCancelledError: 409,
    RecordAlreadyPublishedError: 409,
    ActionItemAlreadyCompletedError: 409,
    AgendaAlreadyConfirmedError: 409,
    CommentAlreadyExistsError: 409,
    DuplicateMembershipError: 409,
    CircularHierarchyError: 409,
    NoPendingConfirmationRequestError: 409,
    ScheduleCancelledError: 409,
    SameUserError: 409,
    # -------------------------------------------------------
    # 422 Unprocessable Entity -- validation / business rule
    # -------------------------------------------------------
    InvalidReminderMinutesError: 422,
    InvalidScheduleOperationError: 422,
    RecordNotPublishedError: 422,
    InvalidLimitError: 422,
    InvalidPaginationError: 422,
    InvalidTopicError: 422,
    InvalidTemplateNameError: 422,
    InvalidScheduleTitleError: 422,
    PreparationInvalidCommentBodyError: 422,
    RecordInvalidCommentBodyError: 422,
    InvalidActionItemTitleError: 422,
    InvalidMemoError: 422,
    InvalidWorkspaceNameError: 422,
    AgendaEditNotAllowedError: 422,
    InconsistentScheduleAgendasError: 422,
    InconsistentSchedulesError: 422,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for all mapped domain/application exceptions.

    Each exception class in ``EXCEPTION_STATUS_MAP`` gets a handler that
    returns a JSON response with the corresponding HTTP status code and
    a ``{"detail": "..."}`` body.

    Unmapped exceptions will fall through to FastAPI's default 500 handler.
    """

    for exc_cls, status_code in EXCEPTION_STATUS_MAP.items():

        def _make_handler(
            code: int,
        ) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
            async def _handler(_request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(
                    status_code=code,
                    content={"detail": str(exc)},
                )

            return _handler

        app.add_exception_handler(exc_cls, _make_handler(status_code))
