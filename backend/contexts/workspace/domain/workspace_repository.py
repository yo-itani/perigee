from __future__ import annotations

from abc import ABC, abstractmethod

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace


class WorkspaceRepository(ABC):
    """Repository interface for Workspace aggregate.

    Circular hierarchy validation is performed at the application layer
    using get_ancestors().
    """

    @abstractmethod
    async def get(self, workspace_id: WorkspaceId) -> Workspace | None:
        """Retrieve a workspace by ID, or None if not found."""

    @abstractmethod
    async def save(self, workspace: Workspace) -> None:
        """Persist a workspace (create or update)."""

    @abstractmethod
    async def get_ancestors(self, workspace_id: WorkspaceId) -> list[Workspace]:
        """Retrieve all ancestor workspaces (parent, grandparent, ...).

        Used by the application layer to verify that a hierarchy change
        does not introduce a circular reference.

        Returns ancestors ordered from immediate parent to root.
        """
