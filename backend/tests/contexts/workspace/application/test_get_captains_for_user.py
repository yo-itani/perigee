"""Tests for GetCaptainsForUserQueryService."""

from __future__ import annotations

from datetime import datetime

from contexts.workspace.application.get_captains_for_user import (
    GetCaptainsForUserInput,
    GetCaptainsForUserOutput,
    GetCaptainsForUserQueryService,
)
from contexts.workspace.domain.value_objects import MembershipRole
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from shared.domain.value_objects import UserId
from tests.contexts.workspace.application.conftest import InMemoryWorkspaceRepository


def _build_use_case(
    repo: InMemoryWorkspaceRepository | None = None,
) -> tuple[GetCaptainsForUserQueryService, InMemoryWorkspaceRepository]:
    r = repo or InMemoryWorkspaceRepository()
    uc = GetCaptainsForUserQueryService(workspace_repository=r)
    return uc, r


def _make_workspace(
    name: str = "ws",
    parent_id: None = None,
) -> Workspace:
    return Workspace.create(
        name=WorkspaceName(name),
        parent_id=parent_id,
        now=datetime(2026, 1, 1),
    )


class TestGetCaptainsForUser:
    """Tests for successful Captain retrieval."""

    async def test_returns_captains_from_direct_workspace(self) -> None:
        """Captains in the user's direct workspace are returned."""
        user = UserId.generate()
        captain = UserId.generate()
        ws = _make_workspace("team")
        ws.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        ws.add_member(
            user_id=captain, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws.collect_events()

        uc, repo = _build_use_case()
        await repo.save(ws)

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert isinstance(output, GetCaptainsForUserOutput)
        assert captain in output.captain_ids
        assert len(output.captain_ids) == 1

    async def test_returns_captains_from_ancestor_workspaces(self) -> None:
        """Captains in ancestor workspaces are included."""
        user = UserId.generate()
        captain_parent = UserId.generate()
        captain_child = UserId.generate()

        parent_ws = _make_workspace("parent")
        parent_ws.add_member(
            user_id=captain_parent,
            role=MembershipRole.CAPTAIN,
            now=datetime(2026, 1, 1),
        )
        parent_ws.collect_events()

        child_ws = Workspace.create(
            name=WorkspaceName("child"),
            parent_id=parent_ws.id,
            now=datetime(2026, 1, 1),
        )
        child_ws.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        child_ws.add_member(
            user_id=captain_child,
            role=MembershipRole.CAPTAIN,
            now=datetime(2026, 1, 1),
        )
        child_ws.collect_events()

        uc, repo = _build_use_case()
        await repo.save(parent_ws)
        await repo.save(child_ws)

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert captain_child in output.captain_ids
        assert captain_parent in output.captain_ids
        assert len(output.captain_ids) == 2

    async def test_deduplicates_captains_across_workspaces(self) -> None:
        """Same Captain appearing in multiple workspaces is deduplicated."""
        user = UserId.generate()
        captain = UserId.generate()

        ws1 = _make_workspace("ws1")
        ws1.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        ws1.add_member(
            user_id=captain, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws1.collect_events()

        ws2 = _make_workspace("ws2")
        ws2.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        ws2.add_member(
            user_id=captain, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws2.collect_events()

        uc, repo = _build_use_case()
        await repo.save(ws1)
        await repo.save(ws2)

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert output.captain_ids == [captain]

    async def test_excludes_the_user_themselves(self) -> None:
        """If the user is also a Captain, they are excluded."""
        user = UserId.generate()

        ws = _make_workspace("team")
        ws.add_member(
            user_id=user, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws.collect_events()

        uc, repo = _build_use_case()
        await repo.save(ws)

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert output.captain_ids == []

    async def test_returns_empty_when_user_has_no_workspaces(self) -> None:
        """User with no memberships gets empty result."""
        user = UserId.generate()
        uc, _repo = _build_use_case()

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert output.captain_ids == []

    async def test_handles_multiple_workspace_memberships(self) -> None:
        """User in multiple workspaces gets Captains from all."""
        user = UserId.generate()
        captain_a = UserId.generate()
        captain_b = UserId.generate()

        ws_a = _make_workspace("A")
        ws_a.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        ws_a.add_member(
            user_id=captain_a, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws_a.collect_events()

        ws_b = _make_workspace("B")
        ws_b.add_member(
            user_id=user, role=MembershipRole.MEMBER, now=datetime(2026, 1, 1)
        )
        ws_b.add_member(
            user_id=captain_b, role=MembershipRole.CAPTAIN, now=datetime(2026, 1, 1)
        )
        ws_b.collect_events()

        uc, repo = _build_use_case()
        await repo.save(ws_a)
        await repo.save(ws_b)

        output = await uc.execute(GetCaptainsForUserInput(user_id=user))

        assert set(output.captain_ids) == {captain_a, captain_b}
