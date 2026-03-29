"""Use case: Rename a workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace_name import WorkspaceName
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace is not found."""

    def __init__(self, message: str = "Workspace not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class RenameWorkspaceInput:
    """Input DTO for workspace rename."""

    workspace_id: WorkspaceId
    new_name: WorkspaceName


class RenameWorkspaceUseCase:
    """Application service that renames an existing workspace."""

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
        input_dto: RenameWorkspaceInput,
    ) -> None:
        """Rename the workspace.

        Args:
            input_dto: The input containing workspace id and new name.

        Raises:
            WorkspaceNotFoundError: If the workspace does not exist.
        """
        now = datetime.now(UTC)

        async with self._uow:
            workspace = await self._workspace_repo.get_by_id(input_dto.workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError()

            workspace.rename(new_name=input_dto.new_name, now=now)
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())

        await self._event_dispatcher.dispatch(events)
