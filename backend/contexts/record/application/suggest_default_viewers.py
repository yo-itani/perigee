"""Use case: Suggest default viewers for a Record.

At publish-screen display time, suggest Captains from the counterpart's
Workspace ancestry as default viewers. This is a read-only query that
delegates to the CaptainQueryService (dependency inversion).
"""

from __future__ import annotations

from dataclasses import dataclass

from contexts.record.domain.captain_query_service import CaptainQueryService
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
class SuggestDefaultViewersInput:
    """Input DTO for SuggestDefaultViewersUseCase."""

    record_id: RecordId
    actor_id: UserId


@dataclass(frozen=True)
class SuggestDefaultViewersOutput:
    """Output DTO for SuggestDefaultViewersUseCase."""

    suggested_viewer_ids: list[UserId]


class SuggestDefaultViewersUseCase:
    """Suggest default viewers based on the counterpart's Captain hierarchy.

    Workflow:
    1. Load the record and verify it exists.
    2. Use CaptainQueryService to get Captains for the counterpart.
    3. Return the deduplicated list (excluding organizer and counterpart,
       as they are implicitly included).

    This is a read-only query; no UnitOfWork or EventDispatcher needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        captain_query_service: CaptainQueryService,
    ) -> None:
        self._record_repository = record_repository
        self._captain_query_service = captain_query_service

    async def execute(
        self, input_dto: SuggestDefaultViewersInput
    ) -> SuggestDefaultViewersOutput:
        record = await self._record_repository.get_by_id(input_dto.record_id)
        if record is None:
            raise RecordNotFoundError(input_dto.record_id)

        if input_dto.actor_id != record.organizer_id:
            raise UnauthorizedOperationError(
                "Only the organizer can suggest default viewers."
            )

        captain_ids = await self._captain_query_service.get_captains_for_user(
            record.counterpart_id
        )

        # Exclude organizer and counterpart (they are implicit)
        implicit = {record.organizer_id, record.counterpart_id}
        suggested = [uid for uid in captain_ids if uid not in implicit]

        return SuggestDefaultViewersOutput(suggested_viewer_ids=suggested)
