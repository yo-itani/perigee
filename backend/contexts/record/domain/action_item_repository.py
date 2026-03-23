from __future__ import annotations

from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.value_objects import ActionItemId
from foundation.domain.base_repository import BaseRepository


class ActionItemRepository(BaseRepository[ActionItem, ActionItemId]):
    """Repository interface for ActionItem aggregates."""

    pass  # get_by_id + save (insert or update)
