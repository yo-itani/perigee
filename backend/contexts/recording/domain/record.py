from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from contexts.recording.domain.events import (
    MemoUpdated,
    RecordCreated,
    RecordDraftSaved,
)
from contexts.recording.domain.value_objects import RecordId, RecordStatus
from shared.domain.value_objects import ScheduleId, UserId


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
    status: RecordStatus
    conducted_at: datetime
    created_at: datetime
    updated_at: datetime
    events: list[RecordCreated | MemoUpdated | RecordDraftSaved] = field(
        default_factory=list, repr=False
    )

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
        ts = now or datetime.now()
        record = Record(
            id=record_id,
            organizer_id=organizer_id,
            counterpart_id=counterpart_id,
            schedule_id=schedule_id,
            memo="",
            status=RecordStatus.DRAFT,
            conducted_at=conducted_at,
            created_at=ts,
            updated_at=ts,
        )
        record.events.append(
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
        self.memo = memo
        self.updated_at = now
        self.events.append(
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
        self.events.append(
            RecordDraftSaved(
                record_id=self.id,
                organizer_id=self.organizer_id,
                saved_at=now,
            )
        )

    def is_visible_to(self, user_id: UserId) -> bool:
        """Check if the record is visible to a given user.

        Draft records are only visible to the organizer.
        Published records visibility is managed by the Publishing context.
        """
        if self.status == RecordStatus.DRAFT:
            return user_id == self.organizer_id
        return True

    def _assert_organizer(self, actor_id: UserId) -> None:
        if actor_id != self.organizer_id:
            raise PermissionError("Only the organizer can edit the record.")

    def _assert_draft(self) -> None:
        if self.status != RecordStatus.DRAFT:
            raise ValueError("Record is not in draft status.")
