from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class WorkspaceId:
    """Workspace identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> WorkspaceId:
        return WorkspaceId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> WorkspaceId:
        return WorkspaceId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class MembershipId:
    """Membership identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> MembershipId:
        return MembershipId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> MembershipId:
        return MembershipId(value=uuid.UUID(raw))


class MembershipRole(Enum):
    """Role of a member in a workspace: Captain or Member."""

    CAPTAIN = "captain"
    MEMBER = "member"
