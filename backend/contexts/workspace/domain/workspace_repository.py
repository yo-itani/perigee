from __future__ import annotations

from abc import abstractmethod

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class WorkspaceRepository(BaseRepository[Workspace, WorkspaceId]):
    """Repository interface for Workspace aggregates.

    Extends the base interface with ``get_ancestors`` for
    ancestor-chain cycle detection at the application layer, and
    ``get_by_member_user_id`` for membership lookups.
    """

    @abstractmethod
    async def get_ancestors(self, workspace_id: WorkspaceId) -> list[Workspace]:
        """Return the ancestor chain by following parent_id links.

        The list is ordered from the immediate parent to the root.
        Returns an empty list if the workspace has no parent or
        if the workspace_id does not exist.
        """

    @abstractmethod
    async def get_by_member_user_id(self, user_id: UserId) -> list[Workspace]:
        """Return all workspaces where the given user is a member."""
