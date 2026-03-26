"""Tests for RenameWorkspaceUseCase."""

from __future__ import annotations

import pytest

from contexts.workspace.application.rename_workspace_use_case import (
    RenameWorkspaceInput,
    RenameWorkspaceUseCase,
    WorkspaceNotFoundError,
)
from contexts.workspace.domain.events import WorkspaceRenamed
from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from tests.contexts.workspace.application.conftest import (
    InMemoryWorkspaceRepository,
    StubUnitOfWork,
)


class TestRenameWorkspace:
    """Workspace rename use case."""

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
    ) -> RenameWorkspaceUseCase:
        return RenameWorkspaceUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    async def existing_workspace(
        self,
        repo: InMemoryWorkspaceRepository,
    ) -> Workspace:
        """Pre-populate a workspace in the repository."""
        workspace = Workspace.create(name=WorkspaceName("Engineering"))
        workspace.collect_events()  # clear creation events
        await repo.save(workspace)
        return workspace

    async def test_renames_workspace(
        self,
        service: RenameWorkspaceUseCase,
        repo: InMemoryWorkspaceRepository,
        existing_workspace: Workspace,
    ) -> None:
        """Workspace name is updated in the repository."""
        new_name = WorkspaceName("Platform")

        await service.execute(
            RenameWorkspaceInput(
                workspace_id=existing_workspace.id,
                new_name=new_name,
            )
        )

        updated = await repo.get_by_id(existing_workspace.id)
        assert updated is not None
        assert updated.name == new_name

    async def test_commits_via_uow(
        self,
        service: RenameWorkspaceUseCase,
        uow: StubUnitOfWork,
        existing_workspace: Workspace,
    ) -> None:
        """UoW commit is called after rename."""
        await service.execute(
            RenameWorkspaceInput(
                workspace_id=existing_workspace.id,
                new_name=WorkspaceName("Platform"),
            )
        )

        assert uow.committed is True

    async def test_dispatches_workspace_renamed_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        existing_workspace: Workspace,
    ) -> None:
        """WorkspaceRenamed event is dispatched after commit."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(WorkspaceRenamed, capture_handler)  # type: ignore[arg-type]
        service = RenameWorkspaceUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(
            RenameWorkspaceInput(
                workspace_id=existing_workspace.id,
                new_name=WorkspaceName("Platform"),
            )
        )

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, WorkspaceRenamed)
        assert event.old_name == "Engineering"
        assert event.new_name == "Platform"

    async def test_no_event_when_name_unchanged(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        existing_workspace: Workspace,
    ) -> None:
        """No event is dispatched when the name is the same."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(WorkspaceRenamed, capture_handler)  # type: ignore[arg-type]
        service = RenameWorkspaceUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(
            RenameWorkspaceInput(
                workspace_id=existing_workspace.id,
                new_name=WorkspaceName("Engineering"),
            )
        )

        assert len(dispatched_events) == 0

    async def test_raises_when_workspace_not_found(
        self,
        service: RenameWorkspaceUseCase,
    ) -> None:
        """WorkspaceNotFoundError is raised for a non-existent workspace."""
        with pytest.raises(WorkspaceNotFoundError):
            await service.execute(
                RenameWorkspaceInput(
                    workspace_id=WorkspaceId.generate(),
                    new_name=WorkspaceName("Platform"),
                )
            )
