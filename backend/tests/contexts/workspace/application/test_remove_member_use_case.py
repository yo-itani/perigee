"""Tests for RemoveMemberUseCase."""

from __future__ import annotations

import pytest

from contexts.workspace.application.remove_member_use_case import (
    RemoveMemberInput,
    RemoveMemberUseCase,
    WorkspaceNotFoundError,
)
from contexts.workspace.domain.events import MemberRemoved
from contexts.workspace.domain.exceptions import MembershipNotFoundError
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


class TestRemoveMember:
    """Remove member from workspace use case."""

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
    ) -> RemoveMemberUseCase:
        return RemoveMemberUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    async def workspace_with_member(
        self, repo: InMemoryWorkspaceRepository
    ) -> tuple[Workspace, UserId]:
        """Pre-populate repository with a workspace that has one member."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        user_id = UserId.generate()
        ws.add_member(user_id=user_id, role=MembershipRole.MEMBER, now=ws.created_at)
        ws.collect_events()  # discard creation and add events
        await repo.save(ws)
        return ws, user_id

    async def test_removes_member(
        self,
        service: RemoveMemberUseCase,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """Member is removed from the workspace."""
        ws, user_id = workspace_with_member

        await service.execute(RemoveMemberInput(workspace_id=ws.id, user_id=user_id))

        saved_ws = await repo.get_by_id(ws.id)
        assert saved_ws is not None
        assert len(saved_ws.memberships) == 0

    async def test_commits_via_uow(
        self,
        service: RemoveMemberUseCase,
        uow: StubUnitOfWork,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """UoW commit is called after save."""
        ws, user_id = workspace_with_member

        await service.execute(RemoveMemberInput(workspace_id=ws.id, user_id=user_id))

        assert uow.committed is True

    async def test_dispatches_member_removed_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """MemberRemoved event is dispatched after commit."""
        ws, user_id = workspace_with_member
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(MemberRemoved, capture_handler)  # type: ignore[arg-type]
        service = RemoveMemberUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(RemoveMemberInput(workspace_id=ws.id, user_id=user_id))

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, MemberRemoved)
        assert event.workspace_id == ws.id
        assert event.user_id == user_id

    async def test_raises_when_workspace_not_found(
        self,
        service: RemoveMemberUseCase,
    ) -> None:
        """WorkspaceNotFoundError is raised when workspace does not exist."""
        with pytest.raises(WorkspaceNotFoundError):
            await service.execute(
                RemoveMemberInput(
                    workspace_id=WorkspaceId.generate(),
                    user_id=UserId.generate(),
                )
            )

    async def test_raises_when_membership_not_found(
        self,
        service: RemoveMemberUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """MembershipNotFoundError is raised when user is not a member."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        ws.collect_events()
        await repo.save(ws)

        with pytest.raises(MembershipNotFoundError):
            await service.execute(
                RemoveMemberInput(
                    workspace_id=ws.id,
                    user_id=UserId.generate(),
                )
            )
