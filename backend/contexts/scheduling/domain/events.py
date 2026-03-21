from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.scheduling.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class ScheduleCreated:
    """Raised when a new schedule is created."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    requested_by: UserId
    occurred_at: datetime


@dataclass(frozen=True)
class ScheduleConfirmed:
    """Raised when a schedule is confirmed (manually or automatically)."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    confirmed_by: UserId | None
    is_auto: bool
    occurred_at: datetime


@dataclass(frozen=True)
class ScheduleRejected:
    """Raised when a reschedule proposal is rejected."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    rejected_by: UserId
    occurred_at: datetime


@dataclass(frozen=True)
class ScheduleRescheduled:
    """Raised when a reschedule is proposed."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    new_proposed_at: datetime
    requested_by: UserId
    occurred_at: datetime


@dataclass(frozen=True)
class ScheduleCancelled:
    """Raised when a schedule is cancelled."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    cancelled_by: UserId
    occurred_at: datetime
