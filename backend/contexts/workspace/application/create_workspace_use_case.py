"""Use case: Create a new workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent


class ParentWorkspaceNotFoundError(Exception):
    """Raised when the specified parent workspace does not exist."""

    def __init__(self, message: str = "Parent workspace not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class CreateWorkspaceInput:
    """Input DTO for workspace creation."""

    name: WorkspaceName
    parent_id: WorkspaceId | None = None


@dataclass(frozen=True)
class CreateWorkspaceOutput:
    """Output DTO for workspace creation."""

    workspace_id: WorkspaceId


class CreateWorkspaceUseCase:
    """Application service that creates a new workspace.

    The workspace is optionally placed under a parent workspace.
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
        input_dto: CreateWorkspaceInput,
    ) -> CreateWorkspaceOutput:
        """Create a workspace and return its id.

        Args:
            input_dto: The input containing workspace name and optional parent.

        Returns:
            Output containing the id of the newly created workspace.

        Raises:
            ParentWorkspaceNotFoundError: If the specified parent does not exist.
        """
        now = datetime.now(UTC)

        async with self._uow:
            # Verify that the parent workspace exists when specified.
            if input_dto.parent_id is not None:
                parent = await self._workspace_repo.get_by_id(input_dto.parent_id)
                if parent is None:
                    raise ParentWorkspaceNotFoundError()

            workspace = Workspace.create(
                name=input_dto.name,
                parent_id=input_dto.parent_id,
                now=now,
            )

            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return CreateWorkspaceOutput(workspace_id=workspace.id)
