from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class ScheduleCreated(DomainEvent):
    """Raised when a new schedule is created."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    requested_by: UserId


@dataclass(frozen=True)
class ScheduleConfirmed(DomainEvent):
    """Raised when a schedule is confirmed (manually or automatically)."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    scheduled_at: datetime
    confirmed_by: UserId | None
    is_auto: bool


@dataclass(frozen=True)
class ScheduleRejected(DomainEvent):
    """Raised when a reschedule proposal is rejected."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    rejected_by: UserId


@dataclass(frozen=True)
class ScheduleRescheduled(DomainEvent):
    """Raised when a reschedule is proposed."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    new_proposed_at: datetime
    requested_by: UserId


@dataclass(frozen=True)
class ScheduleCancelled(DomainEvent):
    """Raised when a schedule is cancelled."""

    schedule_id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    cancelled_by: UserId


@dataclass(frozen=True)
class ScheduleRenamed(DomainEvent):
    """Raised when a schedule is renamed."""

    schedule_id: ScheduleId
    new_title: str


# ------------------------------------------------------------------
# ScheduleGroup events
# ------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduleGroupCreated(DomainEvent):
    """Raised when a new schedule group is created."""

    schedule_group_id: ScheduleGroupId
    organizer_id: UserId
    template_id: TemplateId | None


@dataclass(frozen=True)
class ScheduleGroupRenamed(DomainEvent):
    """Raised when a schedule group is renamed."""

    schedule_group_id: ScheduleGroupId
    new_title: str
    renamed_schedule_ids: list[ScheduleId]


@dataclass(frozen=True)
class AgendaAddedViaGroup(DomainEvent):
    """Raised when an agenda topic is added to all schedules via group."""

    schedule_group_id: ScheduleGroupId
    topic: str
    target_schedule_ids: list[ScheduleId]


@dataclass(frozen=True)
class AgendaRemovedViaGroup(DomainEvent):
    """Raised when an agenda topic is removed from all schedules via group."""

    schedule_group_id: ScheduleGroupId
    topic: str
    removed_agenda_ids: list[AgendaId]


# ------------------------------------------------------------------
# Template events
# ------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateSaved(DomainEvent):
    """Raised when a template is saved (created or updated)."""

    template_id: TemplateId
    name: str
    organizer_id: UserId
