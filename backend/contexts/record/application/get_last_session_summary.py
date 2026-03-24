"""Read-only query service: get last session summary for a pair.

Returns the most recent published Record's summary (memo excerpt +
action items) for a given organizer-counterpart pair.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId
from shared.domain.value_objects import UserId

_SUMMARY_MEMO_EXCERPT_LENGTH = 200


@dataclass(frozen=True)
class ActionItemSummaryDTO:
    """Single action item in the session summary."""

    action_item_id: ActionItemId
    content: str
    is_completed: bool
    created_at: datetime


@dataclass(frozen=True)
class GetLastSessionSummaryInput:
    """Input DTO for GetLastSessionSummaryService."""

    actor_id: UserId
    organizer_id: UserId
    counterpart_id: UserId


@dataclass(frozen=True)
class GetLastSessionSummaryOutput:
    """Output DTO for GetLastSessionSummaryService.

    None is returned by execute() when no matching Record exists.
    """

    record_id: RecordId
    conducted_at: datetime
    memo_excerpt: str
    action_items: list[ActionItemSummaryDTO]


class GetLastSessionSummaryService:
    """Query the last session summary for a pair.

    Returns the most recent published Record visible to actor,
    including all action items (completed and pending) for that Record.

    Returns None when no matching Record exists.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        action_item_repository: ActionItemRepository,
    ) -> None:
        self._record_repository = record_repository
        self._action_item_repository = action_item_repository

    async def execute(
        self, input_dto: GetLastSessionSummaryInput
    ) -> GetLastSessionSummaryOutput | None:
        # 1. Get the latest visible published record for the pair
        record = await self._record_repository.get_latest_visible_published_by_pair(
            actor_id=input_dto.actor_id,
            organizer_id=input_dto.organizer_id,
            counterpart_id=input_dto.counterpart_id,
        )

        if record is None:
            return None

        # 2. Fetch all action items for that record (created_at asc)
        action_items = await self._action_item_repository.list_by_record_id(record.id)

        # 3. Build output
        return GetLastSessionSummaryOutput(
            record_id=record.id,
            conducted_at=record.conducted_at,
            memo_excerpt=record.memo.value[:_SUMMARY_MEMO_EXCERPT_LENGTH],
            action_items=[
                ActionItemSummaryDTO(
                    action_item_id=ai.id,
                    content=ai.title.value,
                    is_completed=ai.is_completed,
                    created_at=ai.created_at,
                )
                for ai in action_items
            ],
        )
