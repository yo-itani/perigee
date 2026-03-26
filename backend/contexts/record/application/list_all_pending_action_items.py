"""Read-only query service: list all pending action items for an organizer.

Returns all incomplete action items across all counterparts where the
logged-in user is the organizer of the originating Record. This is used
by the dashboard to show a cross-counterpart overview.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class AllPendingActionItemDTO:
    """Single pending action item with its originating Record info."""

    action_item_id: ActionItemId
    content: str
    created_at: datetime
    record_id: RecordId
    counterpart_id: UserId
    conducted_at: datetime


@dataclass(frozen=True)
class ListAllPendingActionItemsInput:
    """Input DTO for ListAllPendingActionItemsQueryService."""

    actor_id: UserId
    limit: int = 50


@dataclass(frozen=True)
class ListAllPendingActionItemsOutput:
    """Output DTO for ListAllPendingActionItemsQueryService."""

    items: list[AllPendingActionItemDTO]


MAX_LIMIT = 200


class InvalidLimitError(Exception):
    """limit must be between 1 and MAX_LIMIT (inclusive)."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"limit must be between 1 and {MAX_LIMIT}, got {limit}")


class ListAllPendingActionItemsQueryService:
    """Query all pending (not completed) action items for an organizer.

    Returns action items across all counterparts where the actor is the
    organizer of the originating Record. Results are ordered by created_at
    ascending (oldest first), limited to ``limit`` items (default 50).

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        *,
        action_item_repository: ActionItemRepository,
        record_repository: RecordRepository,
    ) -> None:
        self._action_item_repository = action_item_repository
        self._record_repository = record_repository

    async def execute(
        self, input_dto: ListAllPendingActionItemsInput
    ) -> ListAllPendingActionItemsOutput:
        # 0. Validate limit
        if not (1 <= input_dto.limit <= MAX_LIMIT):
            raise InvalidLimitError(input_dto.limit)

        # 1. Fetch pending action items for this organizer (across all counterparts)
        pending_items = await self._action_item_repository.list_pending_by_organizer(
            input_dto.actor_id,
            limit=input_dto.limit,
        )

        # 2. Collect record IDs to look up Record info
        record_ids = {item.record_id for item in pending_items}
        records_by_id: dict[RecordId, tuple[UserId, datetime]] = {}
        for rid in record_ids:
            record = await self._record_repository.get_by_id(rid)
            if record is not None:
                records_by_id[rid] = (record.counterpart_id, record.conducted_at)

        # 3. Build output DTOs
        result_items: list[AllPendingActionItemDTO] = []
        for item in pending_items:
            record_info = records_by_id.get(item.record_id)
            if record_info is None:
                continue  # skip orphaned items (should not happen in practice)
            counterpart_id, conducted_at = record_info
            result_items.append(
                AllPendingActionItemDTO(
                    action_item_id=item.id,
                    content=item.title.value,
                    created_at=item.created_at,
                    record_id=item.record_id,
                    counterpart_id=counterpart_id,
                    conducted_at=conducted_at,
                )
            )

        return ListAllPendingActionItemsOutput(items=result_items)
