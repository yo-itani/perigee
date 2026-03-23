from __future__ import annotations

from dataclasses import dataclass

from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class WorkspaceCreated(DomainEvent):
    """Raised when a new workspace is created."""

    workspace_id: WorkspaceId
    name: str
    parent_id: WorkspaceId | None


@dataclass(frozen=True)
class WorkspaceRenamed(DomainEvent):
    """Raised when a workspace is renamed."""

    workspace_id: WorkspaceId
    old_name: str
    new_name: str


@dataclass(frozen=True)
class WorkspaceHierarchyChanged(DomainEvent):
    """Raised when a workspace's parent is changed."""

    workspace_id: WorkspaceId
    old_parent_id: WorkspaceId | None
    new_parent_id: WorkspaceId | None


@dataclass(frozen=True)
class MemberAdded(DomainEvent):
    """Raised when a member is added to a workspace."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId
    role: MembershipRole


@dataclass(frozen=True)
class MemberRemoved(DomainEvent):
    """Raised when a member is removed from a workspace."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId


@dataclass(frozen=True)
class MemberRoleChanged(DomainEvent):
    """Raised when a member's role is changed (Captain <-> Member)."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId
    old_role: MembershipRole
    new_role: MembershipRole
