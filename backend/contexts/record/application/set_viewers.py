"""Use case: Set viewers for a Record.

The organizer can add or change the viewers list. This is allowed
both before and after publication. After a successful commit the
ViewersChanged domain event is dispatched.

ReadStatus management:
- Added viewers get a ReadStatus with last_viewed_at set to now,
  so past events are treated as read and only future events are unread.
- Removed viewers have their ReadStatus deleted, since they no longer
  have viewing permission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.read_status_repository import ReadStatusRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class SetViewersInput:
    """Input DTO for SetViewersUseCase."""

    record_id: RecordId
    actor_id: UserId
    viewer_ids: list[UserId]


@dataclass(frozen=True)
class SetViewersOutput:
    """Output DTO for SetViewersUseCase."""

    record_id: RecordId


class SetViewersUseCase:
    """Set the viewers list for a record.

    Workflow:
    1. Load the record and verify it exists.
    2. Capture the current viewers before modification.
    3. Delegate to the domain method (organizer check + dedup).
    4. Determine added/removed viewers and manage ReadStatus accordingly.
    5. Save within a transaction.
    6. Dispatch domain events after commit.

    Note: set_viewers is allowed both before and after publication.
    The domain method handles organizer-only enforcement.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        read_status_repository: ReadStatusRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._read_status_repository = read_status_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(self, input_dto: SetViewersInput) -> SetViewersOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            # Capture current viewers before modification
            previous_viewers = set(record.viewers)

            record.set_viewers(
                viewer_ids=input_dto.viewer_ids,
                actor_id=input_dto.actor_id,
                now=now,
            )

            # Determine added and removed viewers
            current_viewers = set(record.viewers)
            added_viewers = current_viewers - previous_viewers
            removed_viewers = previous_viewers - current_viewers

            await self._record_repository.save(record)

            # Create ReadStatus for added viewers (last_viewed_at = now)
            for viewer_id in added_viewers:
                read_status = ReadStatus.create(
                    record_id=record.id,
                    user_id=viewer_id,
                    now=now,
                )
                await self._read_status_repository.upsert(read_status)

            # Delete ReadStatus for removed viewers
            for viewer_id in removed_viewers:
                await self._read_status_repository.delete_by_record_and_user(
                    record_id=record.id,
                    user_id=viewer_id,
                )

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(record.collect_events())
        await self._event_dispatcher.dispatch(events)

        return SetViewersOutput(record_id=record.id)
