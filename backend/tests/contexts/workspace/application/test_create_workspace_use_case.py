"""Tests for CreateWorkspaceUseCase."""

from __future__ import annotations

import pytest

from contexts.workspace.application.create_workspace_use_case import (
    CreateWorkspaceInput,
    CreateWorkspaceOutput,
    CreateWorkspaceUseCase,
    ParentWorkspaceNotFoundError,
)
from contexts.workspace.domain.events import WorkspaceCreated
from contexts.workspace.domain.value_objects import WorkspaceId
from contexts.workspace.domain.workspace_name import WorkspaceName
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from tests.contexts.workspace.application.conftest import (
    InMemoryWorkspaceRepository,
    StubUnitOfWork,
)


class TestCreateWorkspace:
    """Workspace creation use case."""

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
    ) -> CreateWorkspaceUseCase:
        return CreateWorkspaceUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_root_workspace(
        self,
        service: CreateWorkspaceUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Root workspace (no parent) is persisted correctly."""
        name = WorkspaceName("Engineering")

        output = await service.execute(CreateWorkspaceInput(name=name))

        assert isinstance(output, CreateWorkspaceOutput)
        workspace = await repo.get_by_id(output.workspace_id)
        assert workspace is not None
        assert workspace.name == name
        assert workspace.parent_id is None

    async def test_creates_child_workspace(
        self,
        service: CreateWorkspaceUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Child workspace is linked to the specified parent."""
        parent_output = await service.execute(
            CreateWorkspaceInput(name=WorkspaceName("Engineering"))
        )

        child_output = await service.execute(
            CreateWorkspaceInput(
                name=WorkspaceName("Backend"),
                parent_id=parent_output.workspace_id,
            )
        )

        child = await repo.get_by_id(child_output.workspace_id)
        assert child is not None
        assert child.parent_id == parent_output.workspace_id

    async def test_commits_via_uow(
        self,
        service: CreateWorkspaceUseCase,
        uow: StubUnitOfWork,
    ) -> None:
        """UoW commit is called after save."""
        await service.execute(CreateWorkspaceInput(name=WorkspaceName("Engineering")))

        assert uow.committed is True

    async def test_dispatches_workspace_created_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """WorkspaceCreated event is dispatched after commit."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(WorkspaceCreated, capture_handler)  # type: ignore[arg-type]
        service = CreateWorkspaceUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(CreateWorkspaceInput(name=WorkspaceName("Engineering")))

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, WorkspaceCreated)
        assert event.name == "Engineering"
        assert event.parent_id is None

    async def test_raises_when_parent_workspace_not_found(
        self,
        service: CreateWorkspaceUseCase,
    ) -> None:
        """ParentWorkspaceNotFoundError is raised when parent_id does not exist."""
        with pytest.raises(ParentWorkspaceNotFoundError):
            await service.execute(
                CreateWorkspaceInput(
                    name=WorkspaceName("Backend"),
                    parent_id=WorkspaceId.generate(),
                )
            )
