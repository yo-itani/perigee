"""Shared test doubles for workspace application tests."""

from __future__ import annotations

from types import TracebackType

from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from shared.domain.value_objects import UserId


class StubUnitOfWork(UnitOfWork):
    """In-memory UoW that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> StubUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class InMemoryWorkspaceRepository(WorkspaceRepository):
    """In-memory workspace repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[WorkspaceId, Workspace] = {}

    async def get_by_id(self, entity_id: WorkspaceId) -> Workspace | None:
        return self._store.get(entity_id)

    async def save(self, entity: Workspace) -> None:
        self._store[entity.id] = entity

    async def get_ancestors(self, workspace_id: WorkspaceId) -> list[Workspace]:
        """Walk parent_id links to build ancestor chain."""
        ancestors: list[Workspace] = []
        current_id: WorkspaceId | None = workspace_id
        visited: set[WorkspaceId] = set()

        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            workspace = self._store.get(current_id)
            if workspace is None:
                break
            ancestors.append(workspace)
            current_id = workspace.parent_id

        return ancestors

    async def get_by_member_user_id(self, user_id: UserId) -> list[Workspace]:
        """Return all workspaces where the given user is a member."""
        return [
            ws
            for ws in self._store.values()
            if any(m.user_id == user_id for m in ws.memberships)
        ]

    @property
    def workspaces(self) -> dict[WorkspaceId, Workspace]:
        return dict(self._store)
