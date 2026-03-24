"""Query service interface for Captain lookups (dependency inversion).

The Record context defines what it needs from the Workspace context.
The actual implementation lives outside the Record domain layer and
delegates to the Workspace context's services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.value_objects import UserId


class CaptainQueryService(ABC):
    """Read-only query service that the Record context uses to obtain
    Captain suggestions for default viewers.
    """

    @abstractmethod
    async def get_captains_for_user(self, user_id: UserId) -> list[UserId]:
        """Return deduplicated Captain UserIds for the given user.

        The implementation should:
        - Find all Workspaces where the user is a member
        - Walk up ancestor Workspaces
        - Collect Captain UserIds (excluding the user themselves)
        - Deduplicate by UserId
        """
