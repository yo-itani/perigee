"""Adapter implementing the Record context's CaptainQueryService interface.

Delegates to the Workspace context's CaptainQueryService (application layer)
to look up Captain user IDs for default viewer suggestion. This adapter
bridges the cross-context boundary while keeping the Record domain layer
free of Workspace dependencies.
"""

from __future__ import annotations

from contexts.record.domain.captain_query_service import CaptainQueryService
from contexts.workspace.application.captain_query_service import (
    CaptainQueryInput,
)
from contexts.workspace.application.captain_query_service import (
    CaptainQueryService as WorkspaceCaptainQueryService,
)
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from shared.domain.value_objects import UserId


class WorkspaceCaptainQueryServiceAdapter(CaptainQueryService):
    """Adapter that delegates to Workspace context's CaptainQueryService.

    The Record domain defines what it needs (CaptainQueryService ABC);
    this infrastructure adapter satisfies that contract by calling into
    the Workspace application layer.
    """

    def __init__(self, *, workspace_repo: WorkspaceRepository) -> None:
        self._workspace_captain_query = WorkspaceCaptainQueryService(workspace_repo)

    async def get_captains_for_user(self, user_id: UserId) -> list[UserId]:
        output = await self._workspace_captain_query.execute(
            CaptainQueryInput(counterpart_id=user_id)
        )
        return output.captain_user_ids
