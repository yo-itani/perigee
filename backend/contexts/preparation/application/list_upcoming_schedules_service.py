"""Use case: List upcoming schedules for a participant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.domain.value_objects import (
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
)
from shared.domain.value_objects import UserId

_DEFAULT_LIMIT = 20

_UPCOMING_STATUSES = [ScheduleStatus.REQUESTED, ScheduleStatus.CONFIRMED]


@dataclass(frozen=True)
class UpcomingScheduleItem:
    """A single item in the upcoming schedules list."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    status: ScheduleStatus
    title: str
    schedule_group_id: ScheduleGroupId | None


@dataclass(frozen=True)
class ListUpcomingSchedulesInput:
    """Input DTO for ListUpcomingSchedulesService."""

    actor_id: UserId
    limit: int = _DEFAULT_LIMIT


@dataclass(frozen=True)
class ListUpcomingSchedulesOutput:
    """Output DTO for ListUpcomingSchedulesService."""

    schedules: list[UpcomingScheduleItem]


class ListUpcomingSchedulesService:
    """Application service that lists upcoming schedules for a participant.

    This is a read-only operation; no UoW or event dispatching is needed.
    """

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self._schedule_repo = schedule_repo

    async def execute(
        self,
        input_dto: ListUpcomingSchedulesInput,
    ) -> ListUpcomingSchedulesOutput:
        """List upcoming schedules where the actor is organizer or counterpart.

        Returns schedules with scheduled_at >= now, excluding CANCELLED,
        sorted by scheduled_at ascending.

        Args:
            input_dto: Input containing the actor ID and optional limit.

        Returns:
            Output containing the list of upcoming schedules.
        """
        now = datetime.now(UTC)

        schedules = await self._schedule_repo.list_upcoming_by_participant(
            user_id=input_dto.actor_id,
            now=now,
            statuses=_UPCOMING_STATUSES,
            limit=input_dto.limit,
        )

        items = [
            UpcomingScheduleItem(
                schedule_id=s.id,
                organizer_id=s.organizer_id,
                counterpart_id=s.counterpart_id,
                scheduled_at=s.scheduled_at,
                status=s.status,
                title=s.title.value,
                schedule_group_id=s.schedule_group_id,
            )
            for s in schedules
        ]

        return ListUpcomingSchedulesOutput(schedules=items)
