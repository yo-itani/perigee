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


@dataclass(frozen=True)
class CreateWorkspaceInput:
    """Input DTO for workspace creation."""

    name: WorkspaceName
    parent_id: WorkspaceId | None = None


@dataclass(frozen=True)
class CreateWorkspaceOutput:
    """Output DTO for workspace creation."""

    workspace_id: WorkspaceId


class CreateWorkspaceService:
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
        """
        now = datetime.now(UTC)

        workspace = Workspace.create(
            name=input_dto.name,
            parent_id=input_dto.parent_id,
            now=now,
        )

        async with self._uow:
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return CreateWorkspaceOutput(workspace_id=workspace.id)
