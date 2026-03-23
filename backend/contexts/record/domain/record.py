from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.events import (
    MemoUpdated,
    RecordCreated,
    RecordDraftSaved,
    RecordPublished,
    ViewersChanged,
)
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.value_objects import RecordId, RecordStatus
from shared.domain.value_objects import UserId

type _RecordEvent = (
    RecordCreated | MemoUpdated | RecordDraftSaved | RecordPublished | ViewersChanged
)


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
    _memo: Memo
    _status: RecordStatus
    _viewers: list[UserId]
    conducted_at: datetime
    created_at: datetime
    _updated_at: datetime
    _events: list[_RecordEvent] = field(default_factory=list, repr=False)

    @property
    def memo(self) -> Memo:
        return self._memo

    @property
    def status(self) -> RecordStatus:
        return self._status

    @property
    def viewers(self) -> list[UserId]:
        return list(self._viewers)

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

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
            _memo=Memo(""),
            _status=RecordStatus.DRAFT,
            _viewers=[],
            conducted_at=conducted_at,
            created_at=ts,
            _updated_at=ts,
        )
        record._events.append(
            RecordCreated(
                occurred_at=ts,
                record_id=record_id,
                organizer_id=organizer_id,
                counterpart_id=counterpart_id,
                schedule_id=schedule_id,
                conducted_at=conducted_at,
            )
        )
        return record

    def update_memo(self, *, memo: Memo, actor_id: UserId, now: datetime) -> None:
        """Update memo content. Only the organizer may edit."""
        self._assert_organizer(actor_id)
        self._assert_draft()
        self._memo = memo
        self._updated_at = now
        self._events.append(
            MemoUpdated(
                occurred_at=now,
                record_id=self.id,
                organizer_id=self.organizer_id,
            )
        )

    def save_draft(self, *, actor_id: UserId, now: datetime) -> None:
        """Save as draft. Only the organizer may save."""
        self._assert_organizer(actor_id)
        self._assert_draft()
        self._updated_at = now
        self._events.append(
            RecordDraftSaved(
                occurred_at=now,
                record_id=self.id,
                organizer_id=self.organizer_id,
            )
        )

    def publish(self, *, actor_id: UserId, now: datetime) -> None:
        """Publish the record. Only the organizer may publish.

        Status transition: Draft -> Published (one-way).
        """
        self._assert_organizer(actor_id)
        self._assert_draft()
        self._status = RecordStatus.PUBLISHED
        self._updated_at = now
        self._events.append(
            RecordPublished(
                occurred_at=now,
                record_id=self.id,
                organizer_id=self.organizer_id,
            )
        )

    def set_viewers(
        self, *, viewer_ids: list[UserId], actor_id: UserId, now: datetime
    ) -> None:
        """Set the viewers list. Only the organizer may change viewers.

        organizer_id and counterpart_id are implicitly included and will be
        excluded from the explicit viewers list. Duplicates are removed.
        """
        self._assert_organizer(actor_id)
        implicit = {self.organizer_id, self.counterpart_id}
        seen: set[UserId] = set()
        deduplicated: list[UserId] = []
        for vid in viewer_ids:
            if vid not in implicit and vid not in seen:
                seen.add(vid)
                deduplicated.append(vid)
        self._viewers = deduplicated
        self._updated_at = now
        self._events.append(
            ViewersChanged(
                occurred_at=now,
                record_id=self.id,
                organizer_id=self.organizer_id,
                viewer_ids=tuple(deduplicated),
            )
        )

    def is_visible_to(self, user_id: UserId) -> bool:
        """Check if the record is visible to a given user.

        Draft records are only visible to the organizer.
        Published records are visible to organizer, counterpart, and viewers.
        """
        if self._status == RecordStatus.DRAFT:
            return user_id == self.organizer_id
        return (
            user_id == self.organizer_id
            or user_id == self.counterpart_id
            or user_id in self._viewers
        )

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
