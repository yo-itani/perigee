from datetime import datetime

import pytest

from contexts.workspace.domain.events import (
    MemberAdded,
    MemberRemoved,
    MemberRoleChanged,
    WorkspaceCreated,
    WorkspaceHierarchyChanged,
    WorkspaceRenamed,
)
from contexts.workspace.domain.exceptions import (
    CircularHierarchyError,
    DuplicateMembershipError,
    MembershipNotFoundError,
)
from contexts.workspace.domain.value_objects import (
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from shared.domain.value_objects import UserId


def _make_workspace(
    *,
    name: str = "Engineering",
    parent_id: WorkspaceId | None = None,
    now: datetime | None = None,
) -> Workspace:
    """Helper to create a workspace with sensible defaults."""
    return Workspace.create(
        name=WorkspaceName(name),
        parent_id=parent_id,
        now=now or datetime(2026, 3, 20, 10, 0),
    )


class TestWorkspaceCreate:
    def test_creates_workspace_with_name(self) -> None:
        ws = _make_workspace(name="Engineering")
        assert ws.name == WorkspaceName("Engineering")

    def test_creates_root_workspace(self) -> None:
        ws = _make_workspace()
        assert ws.parent_id is None

    def test_creates_child_workspace(self) -> None:
        parent_id = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent_id)
        assert ws.parent_id == parent_id

    def test_starts_with_no_memberships(self) -> None:
        ws = _make_workspace()
        assert ws.memberships == []

    def test_sets_timestamps(self) -> None:
        now = datetime(2026, 3, 20, 10, 0)
        ws = _make_workspace(now=now)
        assert ws.created_at == now
        assert ws.updated_at == now

    def test_emits_workspace_created_event(self) -> None:
        now = datetime(2026, 3, 20, 10, 0)
        ws = _make_workspace(name="Engineering", now=now)
        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, WorkspaceCreated)
        assert event.workspace_id == ws.id
        assert event.name == "Engineering"
        assert event.parent_id is None
        assert event.occurred_at == now

    def test_collect_events_clears_list(self) -> None:
        ws = _make_workspace()
        events = ws.collect_events()
        assert len(events) == 1
        assert ws.collect_events() == []


class TestWorkspaceRename:
    def test_renames_workspace(self) -> None:
        ws = _make_workspace(name="Old Name")
        now = datetime(2026, 3, 20, 11, 0)

        ws.rename(new_name=WorkspaceName("New Name"), now=now)

        assert ws.name == WorkspaceName("New Name")
        assert ws.updated_at == now

    def test_emits_workspace_renamed_event(self) -> None:
        ws = _make_workspace(name="Old Name")
        ws.collect_events()  # clear creation event
        now = datetime(2026, 3, 20, 11, 0)

        ws.rename(new_name=WorkspaceName("New Name"), now=now)

        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, WorkspaceRenamed)
        assert event.workspace_id == ws.id
        assert event.old_name == "Old Name"
        assert event.new_name == "New Name"
        assert event.occurred_at == now

    def test_rename_same_name_is_noop(self) -> None:
        ws = _make_workspace(name="Same")
        ws.collect_events()  # clear creation event
        original_updated_at = ws.updated_at
        now = datetime(2026, 3, 20, 11, 0)

        ws.rename(new_name=WorkspaceName("Same"), now=now)

        assert ws.name == WorkspaceName("Same")
        assert ws.updated_at == original_updated_at
        assert ws.collect_events() == []


class TestWorkspaceChangeParent:
    def test_changes_parent(self) -> None:
        ws = _make_workspace()
        new_parent = WorkspaceId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=new_parent, now=now)

        assert ws.parent_id == new_parent
        assert ws.updated_at == now

    def test_changes_to_root(self) -> None:
        parent = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent)
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=None, now=now)

        assert ws.parent_id is None

    def test_emits_hierarchy_changed_event(self) -> None:
        old_parent = WorkspaceId.generate()
        ws = _make_workspace(parent_id=old_parent)
        ws.collect_events()  # clear creation event
        new_parent = WorkspaceId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=new_parent, now=now)

        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, WorkspaceHierarchyChanged)
        assert event.workspace_id == ws.id
        assert event.old_parent_id == old_parent
        assert event.new_parent_id == new_parent
        assert event.occurred_at == now

    def test_self_referencing_parent_raises(self) -> None:
        ws = _make_workspace()
        now = datetime(2026, 3, 20, 11, 0)

        with pytest.raises(CircularHierarchyError):
            ws.change_parent(new_parent_id=ws.id, now=now)

    def test_change_parent_same_value_is_noop(self) -> None:
        parent = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent)
        ws.collect_events()  # clear creation event
        original_updated_at = ws.updated_at
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=parent, now=now)

        assert ws.parent_id == parent
        assert ws.updated_at == original_updated_at
        assert ws.collect_events() == []

    def test_change_parent_none_to_none_is_noop(self) -> None:
        ws = _make_workspace()  # root, parent_id=None
        ws.collect_events()
        original_updated_at = ws.updated_at
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=None, now=now)

        assert ws.parent_id is None
        assert ws.updated_at == original_updated_at
        assert ws.collect_events() == []


class TestWorkspaceAddMember:
    def test_adds_member(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        membership = ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        assert len(ws.memberships) == 1
        assert ws.memberships[0].user_id == user
        assert ws.memberships[0].role == MembershipRole.MEMBER
        assert membership.user_id == user
        assert ws.updated_at == now

    def test_adds_captain(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.add_member(user_id=user, role=MembershipRole.CAPTAIN, now=now)

        assert ws.memberships[0].role == MembershipRole.CAPTAIN

    def test_multiple_captains_allowed(self) -> None:
        ws = _make_workspace()
        user1 = UserId.generate()
        user2 = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.add_member(user_id=user1, role=MembershipRole.CAPTAIN, now=now)
        ws.add_member(user_id=user2, role=MembershipRole.CAPTAIN, now=now)

        captains = [m for m in ws.memberships if m.role == MembershipRole.CAPTAIN]
        assert len(captains) == 2

    def test_duplicate_membership_raises(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        with pytest.raises(DuplicateMembershipError):
            ws.add_member(user_id=user, role=MembershipRole.CAPTAIN, now=now)

    def test_emits_member_added_event(self) -> None:
        ws = _make_workspace()
        ws.collect_events()  # clear creation event
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MemberAdded)
        assert event.workspace_id == ws.id
        assert event.user_id == user
        assert event.role == MembershipRole.MEMBER
        assert event.occurred_at == now

    def test_memberships_property_returns_copy(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        returned = ws.memberships
        returned.clear()

        assert len(ws.memberships) == 1


class TestWorkspaceRemoveMember:
    def test_removes_member(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        ws.remove_member(user_id=user, now=datetime(2026, 3, 20, 12, 0))

        assert len(ws.memberships) == 0

    def test_removes_nonexistent_member_raises(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()

        with pytest.raises(MembershipNotFoundError):
            ws.remove_member(user_id=user, now=datetime(2026, 3, 20, 11, 0))

    def test_emits_member_removed_event(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)
        ws.collect_events()  # clear previous events

        remove_now = datetime(2026, 3, 20, 12, 0)
        ws.remove_member(user_id=user, now=remove_now)

        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MemberRemoved)
        assert event.workspace_id == ws.id
        assert event.user_id == user
        assert event.occurred_at == remove_now

    def test_updates_timestamp(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        ws.add_member(
            user_id=user,
            role=MembershipRole.MEMBER,
            now=datetime(2026, 3, 20, 11, 0),
        )
        remove_now = datetime(2026, 3, 20, 12, 0)

        ws.remove_member(user_id=user, now=remove_now)

        assert ws.updated_at == remove_now


class TestWorkspaceChangeMemberRole:
    def test_changes_role(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)

        ws.change_member_role(
            user_id=user,
            new_role=MembershipRole.CAPTAIN,
            now=datetime(2026, 3, 20, 12, 0),
        )

        assert ws.memberships[0].role == MembershipRole.CAPTAIN

    def test_nonexistent_member_raises(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()

        with pytest.raises(MembershipNotFoundError):
            ws.change_member_role(
                user_id=user,
                new_role=MembershipRole.CAPTAIN,
                now=datetime(2026, 3, 20, 11, 0),
            )

    def test_emits_member_role_changed_event(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)
        ws.collect_events()  # clear previous events

        change_now = datetime(2026, 3, 20, 12, 0)
        ws.change_member_role(
            user_id=user, new_role=MembershipRole.CAPTAIN, now=change_now
        )

        events = ws.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MemberRoleChanged)
        assert event.workspace_id == ws.id
        assert event.user_id == user
        assert event.old_role == MembershipRole.MEMBER
        assert event.new_role == MembershipRole.CAPTAIN
        assert event.occurred_at == change_now

    def test_updates_timestamp(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        ws.add_member(
            user_id=user,
            role=MembershipRole.MEMBER,
            now=datetime(2026, 3, 20, 11, 0),
        )
        change_now = datetime(2026, 3, 20, 12, 0)

        ws.change_member_role(
            user_id=user, new_role=MembershipRole.CAPTAIN, now=change_now
        )

        assert ws.updated_at == change_now

    def test_change_role_same_value_is_noop(self) -> None:
        ws = _make_workspace()
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)
        ws.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)
        ws.collect_events()  # clear previous events
        original_updated_at = ws.updated_at

        ws.change_member_role(
            user_id=user,
            new_role=MembershipRole.MEMBER,
            now=datetime(2026, 3, 20, 12, 0),
        )

        assert ws.memberships[0].role == MembershipRole.MEMBER
        assert ws.updated_at == original_updated_at
        assert ws.collect_events() == []


class TestWorkspaceHierarchy:
    def test_root_workspace_has_no_parent(self) -> None:
        ws = _make_workspace()
        assert ws.parent_id is None

    def test_child_workspace_references_parent(self) -> None:
        parent_id = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent_id)
        assert ws.parent_id == parent_id

    def test_parent_can_be_changed_to_another(self) -> None:
        parent1 = WorkspaceId.generate()
        parent2 = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent1)
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=parent2, now=now)

        assert ws.parent_id == parent2

    def test_parent_can_be_removed(self) -> None:
        parent = WorkspaceId.generate()
        ws = _make_workspace(parent_id=parent)
        now = datetime(2026, 3, 20, 11, 0)

        ws.change_parent(new_parent_id=None, now=now)

        assert ws.parent_id is None


class TestUserMultipleWorkspaces:
    def test_user_can_belong_to_multiple_workspaces(self) -> None:
        ws1 = _make_workspace(name="Team A")
        ws2 = _make_workspace(name="Team B")
        user = UserId.generate()
        now = datetime(2026, 3, 20, 11, 0)

        ws1.add_member(user_id=user, role=MembershipRole.MEMBER, now=now)
        ws2.add_member(user_id=user, role=MembershipRole.CAPTAIN, now=now)

        assert len(ws1.memberships) == 1
        assert len(ws2.memberships) == 1
        assert ws1.memberships[0].user_id == user
        assert ws2.memberships[0].user_id == user
