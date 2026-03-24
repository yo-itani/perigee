"""Tests for CaptainQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.workspace.application.captain_query_service import (
    CaptainQueryInput,
    CaptainQueryService,
)
from contexts.workspace.domain.value_objects import MembershipRole
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from shared.domain.value_objects import UserId
from tests.contexts.workspace.application.conftest import InMemoryWorkspaceRepository


def _make_workspace(
    *,
    name: str = "ws",
    parent_id: object = None,
    now: datetime | None = None,
) -> Workspace:
    """Helper: create a workspace with an optional parent."""
    from contexts.workspace.domain.value_objects import WorkspaceId

    ws = Workspace.create(
        name=WorkspaceName(name),
        parent_id=parent_id if isinstance(parent_id, WorkspaceId) else None,
        now=now or datetime(2025, 1, 1, tzinfo=UTC),
    )
    ws.collect_events()  # discard creation events
    return ws


class TestCaptainQueryService:
    """Captain query use case for default viewer suggestion."""

    @pytest.fixture
    def repo(self) -> InMemoryWorkspaceRepository:
        return InMemoryWorkspaceRepository()

    @pytest.fixture
    def service(self, repo: InMemoryWorkspaceRepository) -> CaptainQueryService:
        return CaptainQueryService(workspace_repo=repo)

    async def test_returns_empty_when_user_has_no_workspaces(
        self,
        service: CaptainQueryService,
    ) -> None:
        """No workspaces means no captains."""
        result = await service.execute(
            CaptainQueryInput(counterpart_id=UserId.generate()),
        )
        assert result.captain_user_ids == []

    async def test_returns_captains_from_own_workspace(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Captains in the counterpart's own workspace are returned."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        captain = UserId.generate()

        ws = _make_workspace(name="Team A", now=now)
        ws.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        ws.add_member(user_id=captain, role=MembershipRole.CAPTAIN, now=now)
        ws.collect_events()
        await repo.save(ws)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert result.captain_user_ids == [captain]

    async def test_returns_captains_from_ancestor_workspaces(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Captains in ancestor workspaces are included."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        root_captain = UserId.generate()
        mid_captain = UserId.generate()

        # root -> mid -> leaf
        root = _make_workspace(name="Company", now=now)
        root.add_member(user_id=root_captain, role=MembershipRole.CAPTAIN, now=now)
        root.collect_events()
        await repo.save(root)

        mid = _make_workspace(name="Division", parent_id=root.id, now=now)
        mid.add_member(user_id=mid_captain, role=MembershipRole.CAPTAIN, now=now)
        mid.collect_events()
        await repo.save(mid)

        leaf = _make_workspace(name="Team", parent_id=mid.id, now=now)
        leaf.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        leaf.collect_events()
        await repo.save(leaf)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert set(result.captain_user_ids) == {root_captain, mid_captain}

    async def test_deduplicates_captains_across_workspaces(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Same captain in multiple workspaces appears only once."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        shared_captain = UserId.generate()

        ws_a = _make_workspace(name="Team A", now=now)
        ws_a.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        ws_a.add_member(user_id=shared_captain, role=MembershipRole.CAPTAIN, now=now)
        ws_a.collect_events()
        await repo.save(ws_a)

        ws_b = _make_workspace(name="Team B", now=now)
        ws_b.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        ws_b.add_member(user_id=shared_captain, role=MembershipRole.CAPTAIN, now=now)
        ws_b.collect_events()
        await repo.save(ws_b)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert result.captain_user_ids == [shared_captain]

    async def test_deduplicates_captains_across_ancestor_chains(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Captain in shared ancestor of multiple workspaces appears once."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        root_captain = UserId.generate()

        # root -> team_a, root -> team_b, counterpart in both teams
        root = _make_workspace(name="Company", now=now)
        root.add_member(user_id=root_captain, role=MembershipRole.CAPTAIN, now=now)
        root.collect_events()
        await repo.save(root)

        team_a = _make_workspace(name="Team A", parent_id=root.id, now=now)
        team_a.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        team_a.collect_events()
        await repo.save(team_a)

        team_b = _make_workspace(name="Team B", parent_id=root.id, now=now)
        team_b.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        team_b.collect_events()
        await repo.save(team_b)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert result.captain_user_ids == [root_captain]

    async def test_excludes_members_who_are_not_captains(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Regular members are not included in the result."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        captain = UserId.generate()
        regular_member = UserId.generate()

        ws = _make_workspace(name="Team", now=now)
        ws.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        ws.add_member(user_id=captain, role=MembershipRole.CAPTAIN, now=now)
        ws.add_member(user_id=regular_member, role=MembershipRole.MEMBER, now=now)
        ws.collect_events()
        await repo.save(ws)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert result.captain_user_ids == [captain]
        assert regular_member not in result.captain_user_ids

    async def test_multiple_captains_in_single_workspace(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Multiple captains in one workspace are all returned."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        captain_1 = UserId.generate()
        captain_2 = UserId.generate()

        ws = _make_workspace(name="Team", now=now)
        ws.add_member(user_id=counterpart, role=MembershipRole.MEMBER, now=now)
        ws.add_member(user_id=captain_1, role=MembershipRole.CAPTAIN, now=now)
        ws.add_member(user_id=captain_2, role=MembershipRole.CAPTAIN, now=now)
        ws.collect_events()
        await repo.save(ws)

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert set(result.captain_user_ids) == {captain_1, captain_2}

    async def test_deep_hierarchy_traversal(
        self,
        service: CaptainQueryService,
        repo: InMemoryWorkspaceRepository,
    ) -> None:
        """Captains are collected from deeply nested ancestor chains."""
        now = datetime(2025, 1, 1, tzinfo=UTC)
        counterpart = UserId.generate()
        captains = [UserId.generate() for _ in range(5)]

        # Build a chain: ws_0 -> ws_1 -> ws_2 -> ws_3 -> ws_4
        workspaces: list[Workspace] = []
        for i in range(5):
            parent_id = workspaces[i - 1].id if i > 0 else None
            ws = _make_workspace(name=f"Level {i}", parent_id=parent_id, now=now)
            ws.add_member(user_id=captains[i], role=MembershipRole.CAPTAIN, now=now)
            ws.collect_events()
            await repo.save(ws)
            workspaces.append(ws)

        # Counterpart belongs to the deepest workspace
        workspaces[-1].add_member(
            user_id=counterpart, role=MembershipRole.MEMBER, now=now
        )
        workspaces[-1].collect_events()
        await repo.save(workspaces[-1])

        result = await service.execute(
            CaptainQueryInput(counterpart_id=counterpart),
        )
        assert set(result.captain_user_ids) == set(captains)
