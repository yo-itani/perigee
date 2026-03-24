"""Tests for ChangeWorkspaceParentService."""

from __future__ import annotations

import pytest

from contexts.workspace.application.change_workspace_parent_service import (
    ChangeWorkspaceParentInput,
    ChangeWorkspaceParentService,
    WorkspaceNotFoundError,
)
from contexts.workspace.domain.events import WorkspaceHierarchyChanged
from contexts.workspace.domain.exceptions import CircularHierarchyError
from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from tests.contexts.workspace.application.conftest import (
    InMemoryWorkspaceRepository,
    StubUnitOfWork,
)


class TestChangeWorkspaceParent:
    """Workspace parent change use case."""

    @pytest.fixture
    def uow(self) -> StubUnitOfWork:
        return StubUnitOfWork()

    @pytest.fixture
    def repo(self) -> InMemoryWorkspaceRepository:
        return InMemoryWorkspaceRepository()

    @pytest.fixture
    def dispatcher(self) -> InMemoryEventDispatcher:
        return InMemoryEventDispatcher()

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> ChangeWorkspaceParentService:
        return ChangeWorkspaceParentService(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    async def _create_workspace(
        self,
        repo: InMemoryWorkspaceRepository,
        name: str,
        parent_id: WorkspaceId | None = None,
    ) -> Workspace:
        """Helper to create and persist a workspace."""
        workspace = Workspace.create(
            name=WorkspaceName(name),
            parent_id=parent_id,
        )
        workspace.collect_events()  # clear creation events
        await repo.save(workspace)
        return workspace

    async def test_changes_parent(
        self,
        service: ChangeWorkspaceParentService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Workspace is moved under a new parent."""
        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend")

        await service.execute(
            ChangeWorkspaceParentInput(
                workspace_id=child.id,
                new_parent_id=parent.id,
            )
        )

        updated = await repo.get_by_id(child.id)
        assert updated is not None
        assert updated.parent_id == parent.id

    async def test_moves_to_root(
        self,
        service: ChangeWorkspaceParentService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Workspace can be moved to root (parent_id=None)."""
        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend", parent_id=parent.id)

        await service.execute(
            ChangeWorkspaceParentInput(
                workspace_id=child.id,
                new_parent_id=None,
            )
        )

        updated = await repo.get_by_id(child.id)
        assert updated is not None
        assert updated.parent_id is None

    async def test_commits_via_uow(
        self,
        service: ChangeWorkspaceParentService,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """UoW commit is called after parent change."""
        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend")

        await service.execute(
            ChangeWorkspaceParentInput(
                workspace_id=child.id,
                new_parent_id=parent.id,
            )
        )

        assert uow.committed is True

    async def test_dispatches_hierarchy_changed_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """WorkspaceHierarchyChanged event is dispatched after commit."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(WorkspaceHierarchyChanged, capture_handler)  # type: ignore[arg-type]
        service = ChangeWorkspaceParentService(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend")

        await service.execute(
            ChangeWorkspaceParentInput(
                workspace_id=child.id,
                new_parent_id=parent.id,
            )
        )

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, WorkspaceHierarchyChanged)
        assert event.workspace_id == child.id
        assert event.old_parent_id is None
        assert event.new_parent_id == parent.id

    async def test_raises_when_workspace_not_found(
        self,
        service: ChangeWorkspaceParentService,
    ) -> None:
        """WorkspaceNotFoundError is raised for a non-existent workspace."""
        with pytest.raises(WorkspaceNotFoundError):
            await service.execute(
                ChangeWorkspaceParentInput(
                    workspace_id=WorkspaceId.generate(),
                    new_parent_id=None,
                )
            )

    async def test_rejects_self_referencing_parent(
        self,
        service: ChangeWorkspaceParentService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """CircularHierarchyError is raised when setting parent to self."""
        workspace = await self._create_workspace(repo, "Engineering")

        with pytest.raises(CircularHierarchyError):
            await service.execute(
                ChangeWorkspaceParentInput(
                    workspace_id=workspace.id,
                    new_parent_id=workspace.id,
                )
            )

    async def test_rejects_direct_cycle(
        self,
        service: ChangeWorkspaceParentService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """CircularHierarchyError when A->B, then B tries to move under A."""
        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend", parent_id=parent.id)

        with pytest.raises(CircularHierarchyError):
            await service.execute(
                ChangeWorkspaceParentInput(
                    workspace_id=parent.id,
                    new_parent_id=child.id,
                )
            )

    async def test_rejects_indirect_cycle(
        self,
        service: ChangeWorkspaceParentService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """CircularHierarchyError when A->B->C, then A tries to move under C."""
        grandparent = await self._create_workspace(repo, "Company")
        parent = await self._create_workspace(
            repo, "Engineering", parent_id=grandparent.id
        )
        child = await self._create_workspace(repo, "Backend", parent_id=parent.id)

        with pytest.raises(CircularHierarchyError):
            await service.execute(
                ChangeWorkspaceParentInput(
                    workspace_id=grandparent.id,
                    new_parent_id=child.id,
                )
            )

    async def test_no_event_when_parent_unchanged(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """No event is dispatched when the parent is the same."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(WorkspaceHierarchyChanged, capture_handler)  # type: ignore[arg-type]
        service = ChangeWorkspaceParentService(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        parent = await self._create_workspace(repo, "Engineering")
        child = await self._create_workspace(repo, "Backend", parent_id=parent.id)

        await service.execute(
            ChangeWorkspaceParentInput(
                workspace_id=child.id,
                new_parent_id=parent.id,
            )
        )

        assert len(dispatched_events) == 0
