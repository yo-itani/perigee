"""Read-only query service: list 1-on-1 history for a pair.

Returns published Records for a given organizer-counterpart pair,
visible to the requesting actor, with offset-based pagination.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId

_DEFAULT_MEMO_EXCERPT_LENGTH = 100
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


@dataclass(frozen=True)
class OneOnOneHistoryItemDTO:
    """Single history item with excerpt."""

    record_id: RecordId
    organizer_id: UserId
    counterpart_id: UserId
    conducted_at: datetime
    memo_excerpt: str
    schedule_id: ScheduleId | None


@dataclass(frozen=True)
class ListOneOnOneHistoryInput:
    """Input DTO for ListOneOnOneHistoryService."""

    actor_id: UserId
    organizer_id: UserId
    counterpart_id: UserId
    offset: int = 0
    limit: int = _DEFAULT_LIMIT


@dataclass(frozen=True)
class ListOneOnOneHistoryOutput:
    """Output DTO for ListOneOnOneHistoryService."""

    items: list[OneOnOneHistoryItemDTO]
    total_count: int


class InvalidPaginationError(Exception):
    """offset or limit is out of valid range."""


class ListOneOnOneHistoryService:
    """Query published 1-on-1 history for a pair, visible to actor.

    Authorization:
    - Organizer / counterpart: can see all published Records for the pair.
    - Viewer: can see only published Records where they are in the viewers list.

    Visibility filtering is delegated to the repository.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
    ) -> None:
        self._record_repository = record_repository

    async def execute(
        self, input_dto: ListOneOnOneHistoryInput
    ) -> ListOneOnOneHistoryOutput:
        # 0. Validate pagination params
        if input_dto.offset < 0:
            raise InvalidPaginationError(f"offset must be >= 0, got {input_dto.offset}")
        if not (1 <= input_dto.limit <= _MAX_LIMIT):
            raise InvalidPaginationError(
                f"limit must be between 1 and {_MAX_LIMIT}, got {input_dto.limit}"
            )

        # 1. Fetch visible published records for the pair
        records = await self._record_repository.list_visible_published_by_pair(
            actor_id=input_dto.actor_id,
            organizer_id=input_dto.organizer_id,
            counterpart_id=input_dto.counterpart_id,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )

        # 2. Count total visible published records
        total_count = await self._record_repository.count_visible_published_by_pair(
            actor_id=input_dto.actor_id,
            organizer_id=input_dto.organizer_id,
            counterpart_id=input_dto.counterpart_id,
        )

        # 3. Build output DTOs
        items = [
            OneOnOneHistoryItemDTO(
                record_id=r.id,
                organizer_id=r.organizer_id,
                counterpart_id=r.counterpart_id,
                conducted_at=r.conducted_at,
                memo_excerpt=r.memo.value[:_DEFAULT_MEMO_EXCERPT_LENGTH],
                schedule_id=r.schedule_id,
            )
            for r in records
        ]

        return ListOneOnOneHistoryOutput(items=items, total_count=total_count)
