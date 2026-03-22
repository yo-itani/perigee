from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class WorkspaceCreated:
    """Raised when a new workspace is created."""

    workspace_id: WorkspaceId
    name: str
    parent_id: WorkspaceId | None
    occurred_at: datetime


@dataclass(frozen=True)
class WorkspaceRenamed:
    """Raised when a workspace is renamed."""

    workspace_id: WorkspaceId
    old_name: str
    new_name: str
    occurred_at: datetime


@dataclass(frozen=True)
class WorkspaceHierarchyChanged:
    """Raised when a workspace's parent is changed."""

    workspace_id: WorkspaceId
    old_parent_id: WorkspaceId | None
    new_parent_id: WorkspaceId | None
    occurred_at: datetime


@dataclass(frozen=True)
class MemberAdded:
    """Raised when a member is added to a workspace."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId
    role: MembershipRole
    occurred_at: datetime


@dataclass(frozen=True)
class MemberRemoved:
    """Raised when a member is removed from a workspace."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId
    occurred_at: datetime


@dataclass(frozen=True)
class MemberRoleChanged:
    """Raised when a member's role is changed (Captain <-> Member)."""

    membership_id: MembershipId
    workspace_id: WorkspaceId
    user_id: UserId
    old_role: MembershipRole
    new_role: MembershipRole
    occurred_at: datetime
