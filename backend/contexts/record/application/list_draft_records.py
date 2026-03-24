"""Read-only query service: list draft (unpublished) records for an organizer.

Returns DRAFT Records where the actor is the organizer, ordered by
created_at descending. Used by the dashboard to surface unpublished
records and prevent forgotten drafts.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId

_MEMO_EXCERPT_LENGTH = 100


@dataclass(frozen=True)
class DraftRecordItemDTO:
    """Single draft record item with memo excerpt."""

    record_id: RecordId
    counterpart_id: UserId
    conducted_at: datetime
    memo_excerpt: str
    created_at: datetime
    schedule_id: ScheduleId | None


@dataclass(frozen=True)
class ListDraftRecordsInput:
    """Input DTO for ListDraftRecordsService."""

    actor_id: UserId


@dataclass(frozen=True)
class ListDraftRecordsOutput:
    """Output DTO for ListDraftRecordsService."""

    items: list[DraftRecordItemDTO]


class ListDraftRecordsService:
    """Query draft records owned by the actor.

    Authorization:
    - Only the organizer's own drafts are returned.
    - actor_id is used directly as the organizer_id, so there is no
      way to query another user's drafts.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
    ) -> None:
        self._record_repository = record_repository

    async def execute(self, input_dto: ListDraftRecordsInput) -> ListDraftRecordsOutput:
        # Fetch drafts where the actor is the organizer
        records = await self._record_repository.list_drafts_by_organizer(
            organizer_id=input_dto.actor_id,
        )

        # Build output DTOs
        items = [
            DraftRecordItemDTO(
                record_id=r.id,
                counterpart_id=r.counterpart_id,
                conducted_at=r.conducted_at,
                memo_excerpt=r.memo.value[:_MEMO_EXCERPT_LENGTH],
                created_at=r.created_at,
                schedule_id=r.schedule_id,
            )
            for r in records
        ]

        return ListDraftRecordsOutput(items=items)
