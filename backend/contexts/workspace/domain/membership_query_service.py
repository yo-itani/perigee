"""Query service interface for Membership lookups.

This ABC is defined in the Workspace domain layer so that the
Workspace application layer and cross-context adapters can depend
on a stable contract for membership queries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.value_objects import UserId


class MembershipQueryService(ABC):
    """Read-only query service for workspace membership information.

    Unlike WorkspaceRepository (which loads full aggregates), this service
    provides lightweight read-oriented queries that span multiple workspaces.
    """

    @abstractmethod
    async def get_captains_for_user(self, user_id: UserId) -> list[UserId]:
        """Return the UserIds of all Captains in workspaces where the user
        belongs, including ancestor workspaces.

        The result is deduplicated by UserId and excludes the user themselves.
        """
