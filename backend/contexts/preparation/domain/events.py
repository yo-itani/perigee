from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
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


# ------------------------------------------------------------------
# ScheduleGroup events
# ------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduleGroupCreated:
    """Raised when a new schedule group is created."""

    schedule_group_id: ScheduleGroupId
    organizer_id: UserId
    template_id: TemplateId | None
    occurred_at: datetime


@dataclass(frozen=True)
class AgendaAddedViaGroup:
    """Raised when an agenda topic is added to all schedules via group."""

    schedule_group_id: ScheduleGroupId
    topic: str
    target_schedule_ids: list[ScheduleId]
    occurred_at: datetime


@dataclass(frozen=True)
class AgendaRemovedViaGroup:
    """Raised when an agenda topic is removed from all schedules via group."""

    schedule_group_id: ScheduleGroupId
    topic: str
    removed_agenda_ids: list[AgendaId]
    occurred_at: datetime


# ------------------------------------------------------------------
# Template events
# ------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateSaved:
    """Raised when a template is saved (created or updated)."""

    template_id: TemplateId
    name: str
    organizer_id: UserId
    occurred_at: datetime
