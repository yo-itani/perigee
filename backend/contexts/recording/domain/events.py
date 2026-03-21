from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.recording.domain.value_objects import ActionItemId, RecordId
from shared.domain.value_objects import ScheduleId, UserId


@dataclass(frozen=True)
class RecordCreated:
    """Raised when a record is created (post-hoc or schedule-based)."""

    record_id: RecordId
    organizer_id: UserId
    counterpart_id: UserId
    schedule_id: ScheduleId | None
    conducted_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class MemoUpdated:
    """Raised when memo content is recorded or updated."""

    record_id: RecordId
    organizer_id: UserId
    updated_at: datetime


@dataclass(frozen=True)
class RecordDraftSaved:
    """Raised when a record is saved as draft."""

    record_id: RecordId
    organizer_id: UserId
    saved_at: datetime


@dataclass(frozen=True)
class ActionItemAdded:
    """Raised when an action item is added."""

    action_item_id: ActionItemId
    counterpart_id: UserId
    record_id: RecordId
    title: str
    created_at: datetime


@dataclass(frozen=True)
class ActionItemCompleted:
    """Raised when an action item is completed by the counterpart."""

    action_item_id: ActionItemId
    counterpart_id: UserId
    completed_at: datetime
