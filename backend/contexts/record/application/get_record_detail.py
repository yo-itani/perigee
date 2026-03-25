"""Use case: Get Record detail (read-only).

Returns the full record with memo, action items, and confirmed agenda IDs.
Visibility rules apply: draft records are only visible to the organizer;
published records are visible to organizer, counterpart, and viewers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.action_item_repository import ActionItemRepository
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import ActionItemId, RecordId, RecordStatus
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class ActionItemDTO:
    """Action item summary for record detail output."""

    action_item_id: ActionItemId
    title: str
    is_completed: bool
    counterpart_id: UserId
    created_at: datetime


@dataclass(frozen=True)
class GetRecordDetailInput:
    """Input DTO for GetRecordDetailUseCase."""

    record_id: RecordId
    actor_id: UserId


@dataclass(frozen=True)
class GetRecordDetailOutput:
    """Output DTO for GetRecordDetailUseCase."""

    record_id: RecordId
    organizer_id: UserId
    counterpart_id: UserId
    schedule_id: ScheduleId | None
    memo: str
    status: RecordStatus
    confirmed_agenda_ids: list[AgendaId]
    action_items: list[ActionItemDTO]
    conducted_at: datetime
    created_at: datetime
    updated_at: datetime


class GetRecordDetailUseCase:
    """Return the full detail of a record.

    Authorization:
    - Draft records: only the organizer can view.
    - Published records: organizer, counterpart, and viewers can view.

    This is a read-only query; no UoW or EventDispatcher needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        action_item_repository: ActionItemRepository,
    ) -> None:
        self._record_repository = record_repository
        self._action_item_repository = action_item_repository

    async def execute(self, input_dto: GetRecordDetailInput) -> GetRecordDetailOutput:
        record = await self._record_repository.get_by_id(input_dto.record_id)
        if record is None:
            raise RecordNotFoundError(input_dto.record_id)

        if not record.is_visible_to(input_dto.actor_id):
            raise UnauthorizedOperationError(
                "You do not have permission to view this record."
            )

        # Fetch action items for this record
        action_items: list[
            ActionItem
        ] = await self._action_item_repository.list_by_record_id(record.id)

        action_item_dtos = [
            ActionItemDTO(
                action_item_id=ai.id,
                title=ai.title.value,
                is_completed=ai.is_completed,
                counterpart_id=ai.counterpart_id,
                created_at=ai.created_at,
            )
            for ai in action_items
        ]

        return GetRecordDetailOutput(
            record_id=record.id,
            organizer_id=record.organizer_id,
            counterpart_id=record.counterpart_id,
            schedule_id=record.schedule_id,
            memo=record.memo.value,
            status=record.status,
            confirmed_agenda_ids=list(record.confirmed_agenda_ids),
            action_items=action_item_dtos,
            conducted_at=record.conducted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
