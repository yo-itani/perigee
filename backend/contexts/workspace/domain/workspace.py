from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.workspace.domain.events import (
    MemberAdded,
    MemberRemoved,
    MemberRoleChanged,
    WorkspaceCreated,
    WorkspaceHierarchyChanged,
    WorkspaceRenamed,
)
from contexts.workspace.domain.exceptions import (
    DuplicateMembershipError,
    MembershipNotFoundError,
)
from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace_name import WorkspaceName
from shared.domain.value_objects import UserId

type _WorkspaceEvent = (
    WorkspaceCreated
    | WorkspaceRenamed
    | WorkspaceHierarchyChanged
    | MemberAdded
    | MemberRemoved
    | MemberRoleChanged
)


@dataclass
class Membership:
    """Entity: a user's membership in a workspace.

    Managed exclusively through the Workspace aggregate root.
    """

    id: MembershipId
    user_id: UserId
    _role: MembershipRole

    @property
    def role(self) -> MembershipRole:
        return self._role


@dataclass
class Workspace:
    """Aggregate root: a workspace with hierarchical structure and memberships.

    Business rules:
    - Workspace has a recursive parent-child hierarchy (root has no parent).
    - Circular hierarchy validation is handled at the application layer.
    - Duplicate membership is prohibited (same user cannot join twice).
    - Multiple Captains are allowed per workspace.
    - A user can belong to multiple workspaces.
    """

    id: WorkspaceId
    _name: WorkspaceName
    _parent_id: WorkspaceId | None
    _memberships: list[Membership]
    created_at: datetime
    _updated_at: datetime
    _events: list[_WorkspaceEvent] = field(default_factory=list, repr=False)

    @property
    def name(self) -> WorkspaceName:
        return self._name

    @property
    def parent_id(self) -> WorkspaceId | None:
        return self._parent_id

    @property
    def memberships(self) -> list[Membership]:
        return list(self._memberships)

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def collect_events(self) -> list[_WorkspaceEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        *,
        name: WorkspaceName,
        parent_id: WorkspaceId | None = None,
        now: datetime | None = None,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            name: The workspace name (validated value object).
            parent_id: Optional parent workspace ID (None for root).
            now: Current time (defaults to UTC now).
        """
        ts = now or datetime.now(UTC)
        workspace_id = WorkspaceId.generate()

        workspace = Workspace(
            id=workspace_id,
            _name=name,
            _parent_id=parent_id,
            _memberships=[],
            created_at=ts,
            _updated_at=ts,
        )
        workspace._events.append(
            WorkspaceCreated(
                workspace_id=workspace_id,
                name=name.value,
                parent_id=parent_id,
                occurred_at=ts,
            )
        )
        return workspace

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def rename(self, *, new_name: WorkspaceName, now: datetime) -> None:
        """Rename the workspace."""
        old_name = self._name
        self._name = new_name
        self._updated_at = now
        self._events.append(
            WorkspaceRenamed(
                workspace_id=self.id,
                old_name=old_name.value,
                new_name=new_name.value,
                occurred_at=now,
            )
        )

    def change_parent(
        self, *, new_parent_id: WorkspaceId | None, now: datetime
    ) -> None:
        """Change the parent workspace.

        Circular hierarchy validation must be performed at the application
        layer using WorkspaceRepository.get_ancestors() before calling this
        method.
        """
        old_parent_id = self._parent_id
        self._parent_id = new_parent_id
        self._updated_at = now
        self._events.append(
            WorkspaceHierarchyChanged(
                workspace_id=self.id,
                old_parent_id=old_parent_id,
                new_parent_id=new_parent_id,
                occurred_at=now,
            )
        )

    def add_member(
        self, *, user_id: UserId, role: MembershipRole, now: datetime
    ) -> Membership:
        """Add a member to the workspace.

        Raises:
            DuplicateMembershipError: If the user is already a member.
        """
        if self._find_membership_by_user(user_id) is not None:
            raise DuplicateMembershipError()

        membership_id = MembershipId.generate()
        membership = Membership(
            id=membership_id,
            user_id=user_id,
            _role=role,
        )
        self._memberships.append(membership)
        self._updated_at = now
        self._events.append(
            MemberAdded(
                membership_id=membership_id,
                workspace_id=self.id,
                user_id=user_id,
                role=role,
                occurred_at=now,
            )
        )
        return membership

    def remove_member(self, *, user_id: UserId, now: datetime) -> None:
        """Remove a member from the workspace.

        Raises:
            MembershipNotFoundError: If the user is not a member.
        """
        membership = self._find_membership_by_user(user_id)
        if membership is None:
            raise MembershipNotFoundError()

        self._memberships.remove(membership)
        self._updated_at = now
        self._events.append(
            MemberRemoved(
                membership_id=membership.id,
                workspace_id=self.id,
                user_id=user_id,
                occurred_at=now,
            )
        )

    def change_member_role(
        self, *, user_id: UserId, new_role: MembershipRole, now: datetime
    ) -> None:
        """Change a member's role.

        Raises:
            MembershipNotFoundError: If the user is not a member.
        """
        membership = self._find_membership_by_user(user_id)
        if membership is None:
            raise MembershipNotFoundError()

        old_role = membership.role
        membership._role = new_role
        self._updated_at = now
        self._events.append(
            MemberRoleChanged(
                membership_id=membership.id,
                workspace_id=self.id,
                user_id=user_id,
                old_role=old_role,
                new_role=new_role,
                occurred_at=now,
            )
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_membership_by_user(self, user_id: UserId) -> Membership | None:
        """Find a membership by user ID."""
        for membership in self._memberships:
            if membership.user_id == user_id:
                return membership
        return None
