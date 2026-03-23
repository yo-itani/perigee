from __future__ import annotations

from abc import abstractmethod

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from foundation.domain.base_repository import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace, WorkspaceId]):
    """Repository interface for Workspace aggregates.

    Extends the base interface with ``get_ancestors`` for
    ancestor-chain cycle detection at the application layer.
    """

    @abstractmethod
    async def get_ancestors(self, workspace_id: WorkspaceId) -> list[Workspace]:
        """Return the ancestor chain by following parent_id links.

        The list is ordered from the immediate parent to the root.
        Returns an empty list if the workspace has no parent or
        if the workspace_id does not exist.
        """
