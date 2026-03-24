"""Read-only query service: list pending action items for a counterpart.

Returns all incomplete action items tied to a specific counterpart,
along with their originating Record information. This is used by
organizers preparing for a 1-on-1 or by the counterpart themselves.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class PendingActionItemDTO:
    """Single pending action item with its originating Record info."""

    action_item_id: ActionItemId
    content: str
    created_at: datetime
    record_id: RecordId
    organizer_id: UserId
    conducted_at: datetime


@dataclass(frozen=True)
class ListPendingActionItemsInput:
    """Input DTO for ListPendingActionItemsService."""

    actor_id: UserId
    counterpart_id: UserId
    limit: int = 50


@dataclass(frozen=True)
class ListPendingActionItemsOutput:
    """Output DTO for ListPendingActionItemsService."""

    items: list[PendingActionItemDTO]


class ListPendingActionItemsService:
    """Query pending (not completed) action items for a counterpart.

    Authorization: the actor must have participated in at least one
    Record where counterpart_id is the counterpart (as organizer or
    as the counterpart themselves).

    Results are ordered by created_at ascending (oldest first),
    limited to ``limit`` items (default 50).

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
        self, input_dto: ListPendingActionItemsInput
    ) -> ListPendingActionItemsOutput:
        # 1. Authorization: actor must be involved in records with this counterpart
        has_access = await self._record_repository.exists_by_participant(
            user_id=input_dto.actor_id,
            counterpart_id=input_dto.counterpart_id,
        )
        if not has_access:
            raise UnauthorizedOperationError(
                "Actor is not involved in any records with this counterpart."
            )

        # 2. Fetch pending action items
        pending_items = await self._action_item_repository.list_pending_by_counterpart(
            input_dto.counterpart_id,
            limit=input_dto.limit,
        )

        # 3. Collect record IDs to look up Record info
        record_ids = {item.record_id for item in pending_items}
        records_by_id: dict[RecordId, tuple[UserId, datetime]] = {}
        for rid in record_ids:
            record = await self._record_repository.get_by_id(rid)
            if record is not None:
                records_by_id[rid] = (record.organizer_id, record.conducted_at)

        # 4. Build output DTOs
        result_items: list[PendingActionItemDTO] = []
        for item in pending_items:
            record_info = records_by_id.get(item.record_id)
            if record_info is None:
                continue  # skip orphaned items (should not happen in practice)
            organizer_id, conducted_at = record_info
            result_items.append(
                PendingActionItemDTO(
                    action_item_id=item.id,
                    content=item.title.value,
                    created_at=item.created_at,
                    record_id=item.record_id,
                    organizer_id=organizer_id,
                    conducted_at=conducted_at,
                )
            )

        return ListPendingActionItemsOutput(items=result_items)
