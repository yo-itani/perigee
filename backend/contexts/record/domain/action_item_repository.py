from __future__ import annotations

from abc import abstractmethod

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.value_objects import ActionItemId, RecordId
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class ActionItemRepository(BaseRepository[ActionItem, ActionItemId]):
    """Repository interface for ActionItem aggregates."""

    # get_by_id + save (insert or update) inherited from BaseRepository

    @abstractmethod
    async def list_pending_by_counterpart(
        self, counterpart_id: UserId, *, limit: int = 50
    ) -> list[ActionItem]:
        """Return pending (not completed) action items for a counterpart.

        Results are ordered by created_at ascending (oldest first).
        """

    @abstractmethod
    async def list_pending_by_organizer(
        self, organizer_id: UserId, *, limit: int = 50
    ) -> list[ActionItem]:
        """Return pending (not completed) action items across all counterparts
        where the organizer of the originating Record is ``organizer_id``.

        Results are ordered by created_at ascending (oldest first).
        """

    @abstractmethod
    async def list_by_record_id(self, record_id: RecordId) -> list[ActionItem]:
        """Return all action items for a given Record.

        Results are ordered by created_at ascending (oldest first).
        """

    @abstractmethod
    async def delete(self, action_item_id: ActionItemId) -> None:
        """Delete an action item by its identifier."""
