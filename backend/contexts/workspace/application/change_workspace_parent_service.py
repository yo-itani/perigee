"""Use case: Change a workspace's parent (hierarchy change)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.exceptions import CircularHierarchyError
from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace is not found."""

    def __init__(self, message: str = "Workspace not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class ChangeWorkspaceParentInput:
    """Input DTO for workspace parent change."""

    workspace_id: WorkspaceId
    new_parent_id: WorkspaceId | None


class ChangeWorkspaceParentService:
    """Application service that changes a workspace's parent.

    Performs full ancestor-chain cycle detection using
    ``WorkspaceRepository.get_ancestors()`` before delegating
    to the domain entity.
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
        input_dto: ChangeWorkspaceParentInput,
    ) -> None:
        """Change the workspace's parent.

        Args:
            input_dto: The input containing workspace id and new parent id.

        Raises:
            WorkspaceNotFoundError: If the workspace does not exist.
            CircularHierarchyError: If the change would create a cycle.
        """
        now = datetime.now(UTC)

        async with self._uow:
            workspace = await self._workspace_repo.get_by_id(input_dto.workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError()

            # Full ancestor-chain cycle detection:
            # If the new parent is in the ancestor chain of the workspace,
            # moving under it would create a cycle.
            if input_dto.new_parent_id is not None:
                ancestors = await self._workspace_repo.get_ancestors(
                    input_dto.new_parent_id
                )
                ancestor_ids = {a.id for a in ancestors}
                ancestor_ids.add(input_dto.new_parent_id)
                if input_dto.workspace_id in ancestor_ids:
                    raise CircularHierarchyError()

            workspace.change_parent(new_parent_id=input_dto.new_parent_id, now=now)
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)
