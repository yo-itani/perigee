"""Query service: Get Captain user IDs for a given user.

Looks up all Workspaces where the user has a Membership, walks up the
ancestor chain for each, and returns deduplicated Captain UserIds.
This is used by the Record context to suggest default viewers.
"""

from __future__ import annotations

from dataclasses import dataclass

from contexts.workspace.domain.value_objects import MembershipRole
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class GetCaptainsForUserInput:
    """Input DTO for GetCaptainsForUserQueryService."""

    user_id: UserId


@dataclass(frozen=True)
class GetCaptainsForUserOutput:
    """Output DTO for GetCaptainsForUserQueryService."""

    captain_ids: list[UserId]


class GetCaptainsForUserQueryService:
    """Return deduplicated Captain UserIds from all Workspaces the user
    belongs to, including ancestor Workspaces.

    Workflow:
    1. Find all Workspaces where the user is a member.
    2. For each Workspace, walk up ancestors via WorkspaceRepository.
    3. Collect Captain UserIds from each Workspace along the chain.
    4. Deduplicate by UserId, excluding the target user themselves.

    This is a read-only query; no UnitOfWork or EventDispatcher needed.
    """

    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._workspace_repository = workspace_repository

    async def execute(
        self, input_dto: GetCaptainsForUserInput
    ) -> GetCaptainsForUserOutput:
        user_workspaces = await self._workspace_repository.get_by_member_user_id(
            input_dto.user_id
        )

        seen: set[UserId] = set()
        captain_ids: list[UserId] = []

        for ws in user_workspaces:
            # Collect from the workspace itself and its ancestors
            chain = [ws] + await self._workspace_repository.get_ancestors(ws.id)
            for ancestor in chain:
                for m in ancestor.memberships:
                    if (
                        m.role == MembershipRole.CAPTAIN
                        and m.user_id != input_dto.user_id
                        and m.user_id not in seen
                    ):
                        seen.add(m.user_id)
                        captain_ids.append(m.user_id)

        return GetCaptainsForUserOutput(captain_ids=captain_ids)
