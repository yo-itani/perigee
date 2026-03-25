from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.domain.value_objects import (
    ActionItemId,
    CommentId,
    RecordId,
)
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


@dataclass(frozen=True)
class RecordCreated(DomainEvent):
    """Raised when a record is created (post-hoc or schedule-based)."""

    record_id: RecordId
    organizer_id: UserId
    counterpart_id: UserId
    schedule_id: ScheduleId | None
    conducted_at: datetime


@dataclass(frozen=True)
class MemoUpdated(DomainEvent):
    """Raised when memo content is recorded or updated."""

    record_id: RecordId
    organizer_id: UserId


@dataclass(frozen=True)
class AgendaConfirmed(DomainEvent):
    """Raised when an agenda item is confirmed (checked) during a 1-on-1."""

    record_id: RecordId
    agenda_id: AgendaId
    confirmed_by: UserId


@dataclass(frozen=True)
class RecordDraftSaved(DomainEvent):
    """Raised when a record is saved as draft."""

    record_id: RecordId
    organizer_id: UserId


@dataclass(frozen=True)
class RecordPublished(DomainEvent):
    """Raised when a record is published."""

    record_id: RecordId
    organizer_id: UserId


@dataclass(frozen=True)
class ViewersChanged(DomainEvent):
    """Raised when the viewers list of a record is changed."""

    record_id: RecordId
    organizer_id: UserId
    viewer_ids: tuple[UserId, ...]


@dataclass(frozen=True)
class RecordCommentAdded(DomainEvent):
    """Raised when a comment is added to a published record."""

    comment_id: CommentId
    record_id: RecordId
    author_id: UserId


@dataclass(frozen=True)
class ActionItemAdded(DomainEvent):
    """Raised when an action item is added."""

    action_item_id: ActionItemId
    counterpart_id: UserId
    record_id: RecordId
    title: str


@dataclass(frozen=True)
class ActionItemCompleted(DomainEvent):
    """Raised when an action item is completed by the counterpart."""

    action_item_id: ActionItemId
    counterpart_id: UserId


@dataclass(frozen=True)
class ActionItemDeleted(DomainEvent):
    """Raised when an action item is deleted by the organizer."""

    action_item_id: ActionItemId
    record_id: RecordId
    deleted_by: UserId
