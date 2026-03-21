from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.recording.domain.events import (
    MemoUpdated,
    RecordCreated,
    RecordDraftSaved,
    RecordPublished,
)
from contexts.recording.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.recording.domain.value_objects import RecordId, RecordStatus
from shared.domain.value_objects import ScheduleId, UserId

type _RecordEvent = RecordCreated | MemoUpdated | RecordDraftSaved | RecordPublished


@dataclass
class Record:
    """Aggregate root: a 1-on-1 meeting record.

    Business rules:
    - Only the organizer may edit the record.
    - Status transition is one-way: Draft -> Published.
    - A record can exist without a schedule (post-hoc recording).
    - Only published records are visible to counterpart/viewers.
    """

    id: RecordId
    organizer_id: UserId
    counterpart_id: UserId
    schedule_id: ScheduleId | None
    memo: str
    _status: RecordStatus
    conducted_at: datetime
    created_at: datetime
    updated_at: datetime
    _events: list[_RecordEvent] = field(default_factory=list, repr=False)

    @property
    def status(self) -> RecordStatus:
        return self._status

    @staticmethod
    def create(
        *,
        organizer_id: UserId,
        counterpart_id: UserId,
        conducted_at: datetime,
        schedule_id: ScheduleId | None = None,
        now: datetime | None = None,
    ) -> Record:
        """Create a new record in Draft status."""
        record_id = RecordId.generate()
        ts = now or datetime.now(UTC)
        record = Record(
            id=record_id,
            organizer_id=organizer_id,
            counterpart_id=counterpart_id,
            schedule_id=schedule_id,
            memo="",
            _status=RecordStatus.DRAFT,
            conducted_at=conducted_at,
            created_at=ts,
            updated_at=ts,
        )
        record._events.append(
            RecordCreated(
                record_id=record_id,
                organizer_id=organizer_id,
                counterpart_id=counterpart_id,
                schedule_id=schedule_id,
                conducted_at=conducted_at,
                created_at=ts,
            )
        )
        return record

    def update_memo(self, *, memo: str, actor_id: UserId, now: datetime) -> None:
        """Update memo content. Only the organizer may edit."""
        self._assert_organizer(actor_id)
        self._assert_draft()
        self.memo = memo
        self.updated_at = now
        self._events.append(
            MemoUpdated(
                record_id=self.id,
                organizer_id=self.organizer_id,
                updated_at=now,
            )
        )

    def save_draft(self, *, actor_id: UserId, now: datetime) -> None:
        """Save as draft. Only the organizer may save."""
        self._assert_organizer(actor_id)
        self._assert_draft()
        self.updated_at = now
        self._events.append(
            RecordDraftSaved(
                record_id=self.id,
                organizer_id=self.organizer_id,
                saved_at=now,
            )
        )

    def publish(self, *, actor_id: UserId, now: datetime) -> None:
        """Publish the record. Only the organizer may publish.

        Status transition: Draft -> Published (one-way).
        """
        self._assert_organizer(actor_id)
        self._assert_draft()
        self._status = RecordStatus.PUBLISHED
        self.updated_at = now
        self._events.append(
            RecordPublished(
                record_id=self.id,
                organizer_id=self.organizer_id,
                published_at=now,
            )
        )

    def is_visible_to(self, user_id: UserId) -> bool:
        """Check if the record is visible to a given user.

        Draft records are only visible to the organizer.
        Published records visibility is managed by the Publishing context.
        """
        if self._status == RecordStatus.DRAFT:
            return user_id == self.organizer_id
        return True

    def collect_events(self) -> list[_RecordEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events

    def _assert_organizer(self, actor_id: UserId) -> None:
        if actor_id != self.organizer_id:
            raise UnauthorizedOperationError("Only the organizer can edit the record.")

    def _assert_draft(self) -> None:
        if self._status != RecordStatus.DRAFT:
            raise RecordAlreadyPublishedError("Record is already published.")
