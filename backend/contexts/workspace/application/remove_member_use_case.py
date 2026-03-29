"""Use case: Remove a member from a workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.value_objects import WorkspaceId
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
class RemoveMemberInput:
    """Input DTO for removing a member from a workspace."""

    workspace_id: WorkspaceId
    user_id: UserId


class RemoveMemberUseCase:
    """Application service that removes a member from a workspace.

    Domain layer raises MembershipNotFoundError if the user is not a member.
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
        input_dto: RemoveMemberInput,
    ) -> None:
        """Remove a member from the workspace.

        Args:
            input_dto: The input containing workspace id and user id.

        Raises:
            WorkspaceNotFoundError: If the workspace does not exist.
            MembershipNotFoundError: If the user is not a member.
        """
        now = datetime.now(UTC)

        async with self._uow:
            workspace = await self._workspace_repo.get_by_id(input_dto.workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError()

            workspace.remove_member(user_id=input_dto.user_id, now=now)
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())

        await self._event_dispatcher.dispatch(events)
