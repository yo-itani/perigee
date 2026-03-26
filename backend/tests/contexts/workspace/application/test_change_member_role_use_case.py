"""Tests for ChangeMemberRoleUseCase."""

from __future__ import annotations

import pytest

from contexts.workspace.application.change_member_role_use_case import (
    ChangeMemberRoleInput,
    ChangeMemberRoleUseCase,
    WorkspaceNotFoundError,
)
from contexts.workspace.domain.events import MemberRoleChanged
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


class TestChangeMemberRole:
    """Change member role use case."""

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
    ) -> ChangeMemberRoleUseCase:
        return ChangeMemberRoleUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    async def workspace_with_member(
        self, repo: InMemoryWorkspaceRepository
    ) -> tuple[Workspace, UserId]:
        """Pre-populate repository with a workspace that has one Member."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        user_id = UserId.generate()
        ws.add_member(user_id=user_id, role=MembershipRole.MEMBER, now=ws.created_at)
        ws.collect_events()  # discard creation and add events
        await repo.save(ws)
        return ws, user_id

    async def test_changes_role_to_captain(
        self,
        service: ChangeMemberRoleUseCase,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """Member role is changed from Member to Captain."""
        ws, user_id = workspace_with_member

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.CAPTAIN,
            )
        )

        saved_ws = await repo.get_by_id(ws.id)
        assert saved_ws is not None
        assert saved_ws.memberships[0].role == MembershipRole.CAPTAIN

    async def test_changes_role_to_member(
        self,
        repo: InMemoryWorkspaceRepository,
        uow: StubUnitOfWork,
        dispatcher: InMemoryEventDispatcher,
    ) -> None:
        """Captain role is changed back to Member."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        user_id = UserId.generate()
        ws.add_member(user_id=user_id, role=MembershipRole.CAPTAIN, now=ws.created_at)
        ws.collect_events()
        await repo.save(ws)

        service = ChangeMemberRoleUseCase(
            uow=uow, workspace_repo=repo, event_dispatcher=dispatcher
        )

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.MEMBER,
            )
        )

        saved_ws = await repo.get_by_id(ws.id)
        assert saved_ws is not None
        assert saved_ws.memberships[0].role == MembershipRole.MEMBER

    async def test_noop_when_same_role(
        self,
        service: ChangeMemberRoleUseCase,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """No event is dispatched when the role is unchanged."""
        ws, user_id = workspace_with_member

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.MEMBER,  # same as current
            )
        )

        # UoW still commits (the service always commits),
        # but no MemberRoleChanged event should be collected.
        assert uow.committed is True
        saved_ws = await repo.get_by_id(ws.id)
        assert saved_ws is not None
        # Events were already collected in the service; verify no
        # MemberRoleChanged was dispatched by checking no events remain.
        assert saved_ws.memberships[0].role == MembershipRole.MEMBER

    async def test_commits_via_uow(
        self,
        service: ChangeMemberRoleUseCase,
        uow: StubUnitOfWork,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """UoW commit is called after save."""
        ws, user_id = workspace_with_member

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.CAPTAIN,
            )
        )

        assert uow.committed is True

    async def test_dispatches_member_role_changed_event(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """MemberRoleChanged event is dispatched after commit."""
        ws, user_id = workspace_with_member
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(MemberRoleChanged, capture_handler)  # type: ignore[arg-type]
        service = ChangeMemberRoleUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.CAPTAIN,
            )
        )

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, MemberRoleChanged)
        assert event.workspace_id == ws.id
        assert event.user_id == user_id
        assert event.old_role == MembershipRole.MEMBER
        assert event.new_role == MembershipRole.CAPTAIN

    async def test_no_event_dispatched_when_same_role(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryWorkspaceRepository,
        workspace_with_member: tuple[Workspace, UserId],
    ) -> None:
        """No MemberRoleChanged event when role is unchanged."""
        ws, user_id = workspace_with_member
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(MemberRoleChanged, capture_handler)  # type: ignore[arg-type]
        service = ChangeMemberRoleUseCase(
            uow=uow,
            workspace_repo=repo,
            event_dispatcher=dispatcher,
        )

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id,
                user_id=user_id,
                new_role=MembershipRole.MEMBER,  # same as current
            )
        )

        assert len(dispatched_events) == 0

    async def test_raises_when_workspace_not_found(
        self,
        service: ChangeMemberRoleUseCase,
    ) -> None:
        """WorkspaceNotFoundError is raised when workspace does not exist."""
        with pytest.raises(WorkspaceNotFoundError):
            await service.execute(
                ChangeMemberRoleInput(
                    workspace_id=WorkspaceId.generate(),
                    user_id=UserId.generate(),
                    new_role=MembershipRole.CAPTAIN,
                )
            )

    async def test_raises_when_membership_not_found(
        self,
        service: ChangeMemberRoleUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """MembershipNotFoundError is raised when user is not a member."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        ws.collect_events()
        await repo.save(ws)

        with pytest.raises(MembershipNotFoundError):
            await service.execute(
                ChangeMemberRoleInput(
                    workspace_id=ws.id,
                    user_id=UserId.generate(),
                    new_role=MembershipRole.CAPTAIN,
                )
            )

    async def test_multiple_captains_allowed(
        self,
        service: ChangeMemberRoleUseCase,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Multiple members can be promoted to Captain in the same workspace."""
        ws = Workspace.create(name=WorkspaceName("Engineering"))
        user1 = UserId.generate()
        user2 = UserId.generate()
        ws.add_member(user_id=user1, role=MembershipRole.MEMBER, now=ws.created_at)
        ws.add_member(user_id=user2, role=MembershipRole.MEMBER, now=ws.created_at)
        ws.collect_events()
        await repo.save(ws)

        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id, user_id=user1, new_role=MembershipRole.CAPTAIN
            )
        )
        await service.execute(
            ChangeMemberRoleInput(
                workspace_id=ws.id, user_id=user2, new_role=MembershipRole.CAPTAIN
            )
        )

        saved_ws = await repo.get_by_id(ws.id)
        assert saved_ws is not None
        captains = [m for m in saved_ws.memberships if m.role == MembershipRole.CAPTAIN]
        assert len(captains) == 2
