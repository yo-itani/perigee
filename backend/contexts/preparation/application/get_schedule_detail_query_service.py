"""Read-only query service: get schedule detail.

Returns the full detail of a single Schedule for the preparation screen.

No UoW or EventDispatcher needed (read-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.exceptions import UnauthorizedScheduleOperationError
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import (
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
)
from shared.domain.value_objects import UserId


class ScheduleNotFoundError(Exception):
    """Raised when the specified Schedule does not exist."""

    def __init__(self, schedule_id: ScheduleId) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id.value}")


@dataclass(frozen=True)
class GetScheduleDetailInput:
    """Input DTO for GetScheduleDetailQueryService."""

    schedule_id: ScheduleId
    actor_id: UserId


@dataclass(frozen=True)
class GetScheduleDetailOutput:
    """Output DTO for GetScheduleDetailQueryService."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    title: str
    scheduled_at: datetime
    status: ScheduleStatus
    schedule_group_id: ScheduleGroupId | None
    created_at: datetime
    updated_at: datetime


class GetScheduleDetailQueryService:
    """Query the detail of a single Schedule.

    Authorization: the actor must be the organizer or counterpart.

    This is a read-only query service; no UoW or EventDispatcher is needed.
    """

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self._schedule_repo = schedule_repo

    async def execute(
        self, input_dto: GetScheduleDetailInput
    ) -> GetScheduleDetailOutput:
        """Get the schedule detail.

        Args:
            input_dto: Input containing the schedule ID and actor ID.

        Returns:
            Output containing the schedule detail.

        Raises:
            ScheduleNotFoundError: If the schedule does not exist.
            UnauthorizedScheduleOperationError: If actor is not a participant.
        """
        schedule = await self._schedule_repo.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(input_dto.schedule_id)

        # Permission check: only organizer or counterpart
        if (
            input_dto.actor_id != schedule.organizer_id
            and input_dto.actor_id != schedule.counterpart_id
        ):
            raise UnauthorizedScheduleOperationError(
                "Only the organizer or counterpart can view schedule details."
            )

        return GetScheduleDetailOutput(
            schedule_id=schedule.id,
            organizer_id=schedule.organizer_id,
            counterpart_id=schedule.counterpart_id,
            title=schedule.title.value,
            scheduled_at=schedule.scheduled_at,
            status=schedule.status,
            schedule_group_id=schedule.schedule_group_id,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )
