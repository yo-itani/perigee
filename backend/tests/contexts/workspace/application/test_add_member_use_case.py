"""Tests for AddMemberUseCase."""

from __future__ import annotations

import pytest

from contexts.workspace.application.add_member_use_case import (
    AddMemberInput,
    AddMemberOutput,
    AddMemberUseCase,
    WorkspaceNotFoundError,
)
from contexts.workspace.domain.events import MemberAdded
from contexts.workspace.domain.exceptions import DuplicateMembershipError
from contexts.workspace.domain.value_objects import (
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.workspace.application.conftest import (
    InMemoryWorkspaceRepository,
    StubUnitOfWork,
)


class TestAddMember:
    """Add member to workspace use case."""

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
    ) -> AddMemberUseCase:
        return AddMemberUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    async def workspace(self, repo: InMemoryWorkspaceRepository) -> Workspace:
        """Pre-populate repository with a workspace."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        ws.collect_events()  # discard creation event
        await repo.save(ws)
        return ws

    async def test_adds_member_with_default_role(
        self,
        service: AddMemberUseCase,
        repo: InMemoryWorkspaceRepository,
        workspace: Workspace,
    ) -> None:
        """Member is added with default Member role."""
        user_id = UserId.generate()

        output = await service.execute(
            AddMemberInput(workspace_id=workspace.id, user_id=user_id)
        )

        assert isinstance(output, AddMemberOutput)
        ws = await repo.get_by_id(workspace.id)
        assert ws is not None
        assert len(ws.memberships) == 1
        assert ws.memberships[0].user_id == user_id
        assert ws.memberships[0].role == MembershipRole.MEMBER

    async def test_adds_member_as_captain(
        self,
        service: AddMemberUseCase,
        repo: InMemoryWorkspaceRepository,
        workspace: Workspace,
    ) -> None:
        """Member is added with Captain role when specified."""
        user_id = UserId.generate()

        output = await service.execute(
            AddMemberInput(
                workspace_id=workspace.id,
                user_id=user_id,
                role=MembershipRole.CAPTAIN,
            )
        )

        assert isinstance(output, AddMemberOutput)
        ws = await repo.get_by_id(workspace.id)
        assert ws is not None
        assert ws.memberships[0].role == MembershipRole.CAPTAIN

    async def test_commits_via_uow(
        self,
        service: AddMemberUseCase,
        uow: StubUnitOfWork,
        workspace: Workspace,
    ) -> None:
        """UoW commit is called after save."""
        await service.execute(
            AddMemberInput(workspace_id=workspace.id, user_id=UserId.generate())
        )

        assert uow.committed is True

    async def test_dispatches_member_added_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        workspace: Workspace,
    ) -> None:
        """MemberAdded event is dispatched after commit."""
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(MemberAdded, capture_handler)  # type: ignore[arg-type]
        service = AddMemberUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )
        user_id = UserId.generate()

        await service.execute(
            AddMemberInput(workspace_id=workspace.id, user_id=user_id)
        )

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, MemberAdded)
        assert event.workspace_id == workspace.id
        assert event.user_id == user_id
        assert event.role == MembershipRole.MEMBER

    async def test_raises_when_workspace_not_found(
        self,
        service: AddMemberUseCase,
    ) -> None:
        """WorkspaceNotFoundError is raised when workspace does not exist."""
        with pytest.raises(WorkspaceNotFoundError):
            await service.execute(
                AddMemberInput(
                    workspace_id=WorkspaceId.generate(),
                    user_id=UserId.generate(),
                )
            )

    async def test_raises_when_duplicate_membership(
        self,
        service: AddMemberUseCase,
        workspace: Workspace,
    ) -> None:
        """DuplicateMembershipError is raised when user is already a member."""
        user_id = UserId.generate()
        await service.execute(
            AddMemberInput(workspace_id=workspace.id, user_id=user_id)
        )

        with pytest.raises(DuplicateMembershipError):
            await service.execute(
                AddMemberInput(workspace_id=workspace.id, user_id=user_id)
            )

    async def test_user_can_join_multiple_workspaces(
        self,
        service: AddMemberUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """A user can belong to multiple workspaces."""
        ws1 = Workspace.create(name=WorkspaceName("Engineering"))
        ws1.collect_events()
        await repo.save(ws1)

        ws2 = Workspace.create(name=WorkspaceName("Design"))
        ws2.collect_events()
        await repo.save(ws2)

        user_id = UserId.generate()

        await service.execute(AddMemberInput(workspace_id=ws1.id, user_id=user_id))
        await service.execute(AddMemberInput(workspace_id=ws2.id, user_id=user_id))

        saved_ws1 = await repo.get_by_id(ws1.id)
        saved_ws2 = await repo.get_by_id(ws2.id)
        assert saved_ws1 is not None
        assert saved_ws2 is not None
        assert len(saved_ws1.memberships) == 1
        assert len(saved_ws2.memberships) == 1
        assert saved_ws1.memberships[0].user_id == user_id
        assert saved_ws2.memberships[0].user_id == user_id
