"""Use case: Change a member's role in a workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.value_objects import MembershipRole, WorkspaceId
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class WorkspaceNotFoundError(Exception):
    """Raised when the specified workspace does not exist."""

    def __init__(self, message: str = "Workspace not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class ChangeMemberRoleInput:
    """Input DTO for changing a member's role."""

    workspace_id: WorkspaceId
    user_id: UserId
    new_role: MembershipRole


class ChangeMemberRoleUseCase:
    """Application service that changes a member's role in a workspace.

    Domain layer raises MembershipNotFoundError if the user is not a member.
    No-op if the new role is the same as the current role.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        workspace_repo: WorkspaceRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._workspace_repo = workspace_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        input_dto: ChangeMemberRoleInput,
    ) -> None:
        """Change the member's role.

        Args:
            input_dto: The input containing workspace id, user id, and new role.

        Raises:
            WorkspaceNotFoundError: If the workspace does not exist.
            MembershipNotFoundError: If the user is not a member.
        """
        now = datetime.now(UTC)

        async with self._uow:
            workspace = await self._workspace_repo.get_by_id(input_dto.workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError()

            workspace.change_member_role(
                user_id=input_dto.user_id,
                new_role=input_dto.new_role,
                now=now,
            )
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())

        await self._event_dispatcher.dispatch(events)
