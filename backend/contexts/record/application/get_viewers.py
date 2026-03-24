"""Use case: Get viewers for a Record (read-only).

Both the organizer and counterpart can view who the record is shared
with.  Viewers cannot see the viewer list.
"""

from __future__ import annotations

from dataclasses import dataclass

from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class GetViewersInput:
    """Input DTO for GetViewersUseCase."""

    record_id: RecordId
    actor_id: UserId


@dataclass(frozen=True)
class GetViewersOutput:
    """Output DTO for GetViewersUseCase."""

    viewer_ids: list[UserId]


class GetViewersUseCase:
    """Return the current viewers list for a record.

    Only the organizer and counterpart can view the list (per system_design
    section 8 permissions table). This is a read-only query; no UnitOfWork
    or EventDispatcher needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
    ) -> None:
        self._record_repository = record_repository

    async def execute(self, input_dto: GetViewersInput) -> GetViewersOutput:
        record = await self._record_repository.get_by_id(input_dto.record_id)
        if record is None:
            raise RecordNotFoundError(input_dto.record_id)

        if (
            input_dto.actor_id != record.organizer_id
            and input_dto.actor_id != record.counterpart_id
        ):
            raise UnauthorizedOperationError(
                "Only the organizer or counterpart can view the viewers list."
            )

        return GetViewersOutput(viewer_ids=record.viewers)
