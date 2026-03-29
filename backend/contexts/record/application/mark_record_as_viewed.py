"""Use case: Mark a Record as viewed.

When a user opens a Record detail page, the frontend calls
``POST /records/{record_id}/viewed`` which invokes this use case.
It upserts the user's ReadStatus so that ``last_viewed_at`` is set
to the current time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.read_status_repository import ReadStatusRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from foundation.application.unit_of_work import UnitOfWork
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


class RecordNotVisibleError(Exception):
    """Raised when the actor does not have visibility to the record."""

    def __init__(self, record_id: RecordId, user_id: UserId) -> None:
        self.record_id = record_id
        self.user_id = user_id
        super().__init__(f"User {user_id.value} cannot view record {record_id.value}")


@dataclass(frozen=True)
class MarkRecordAsViewedInput:
    """Input DTO for MarkRecordAsViewedUseCase."""

    record_id: RecordId
    actor_id: UserId


class MarkRecordAsViewedUseCase:
    """Mark a record as viewed by the actor.

    Workflow:
    1. Load the record and verify it exists.
    2. Verify the actor has visibility (is_visible_to).
    3. Create a ReadStatus and upsert (insert or update last_viewed_at).
    4. Commit the transaction.

    The upsert approach is safe against concurrent requests: if two
    requests race, the DB-level ``ON DUPLICATE KEY UPDATE`` ensures
    no IntegrityError.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        read_status_repository: ReadStatusRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._record_repository = record_repository
        self._read_status_repository = read_status_repository
        self._unit_of_work = unit_of_work

    async def execute(self, input_dto: MarkRecordAsViewedInput) -> None:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            if not record.is_visible_to(input_dto.actor_id):
                raise RecordNotVisibleError(input_dto.record_id, input_dto.actor_id)

            read_status = ReadStatus.create(
                record_id=input_dto.record_id,
                user_id=input_dto.actor_id,
                now=now,
            )

            await self._read_status_repository.upsert(read_status)
