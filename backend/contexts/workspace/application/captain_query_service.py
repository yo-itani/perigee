"""Use case: Query Captain user IDs for default viewer suggestion."""

from __future__ import annotations

from dataclasses import dataclass

from contexts.workspace.domain.value_objects import MembershipRole
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class CaptainQueryInput:
    """Input DTO for captain query."""

    counterpart_id: UserId


@dataclass(frozen=True)
class CaptainQueryOutput:
    """Output DTO for captain query."""

    captain_user_ids: list[UserId]


class CaptainQueryService:
    """Collect Captain user IDs from a counterpart's workspaces.

    Starting from all workspaces the counterpart belongs to, recursively
    traverses ancestor workspaces and collects users with the Captain role.
    Results are deduplicated by UserId.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(self, workspace_repo: WorkspaceRepository) -> None:
        self._workspace_repo = workspace_repo

    async def execute(self, input_dto: CaptainQueryInput) -> CaptainQueryOutput:
        """Collect Captain user IDs for default viewer suggestion.

        Args:
            input_dto: Contains the counterpart's UserId.

        Returns:
            Output containing deduplicated list of Captain user IDs.
        """
        # 1. Get all workspaces the counterpart belongs to
        workspaces = await self._workspace_repo.get_by_member_user_id(
            input_dto.counterpart_id,
        )

        # 2. For each workspace, collect captains from itself and all ancestors
        captain_ids: dict[UserId, None] = {}

        for ws in workspaces:
            self._collect_captains(ws, captain_ids)

            ancestors = await self._workspace_repo.get_ancestors(ws.id)
            for ancestor in ancestors:
                self._collect_captains(ancestor, captain_ids)

        return CaptainQueryOutput(captain_user_ids=list(captain_ids))

    @staticmethod
    def _collect_captains(
        workspace: Workspace,
        captain_ids: dict[UserId, None],
    ) -> None:
        """Extract Captain user IDs from a workspace's memberships."""
        for membership in workspace.memberships:
            if membership.role == MembershipRole.CAPTAIN:
                captain_ids[membership.user_id] = None
