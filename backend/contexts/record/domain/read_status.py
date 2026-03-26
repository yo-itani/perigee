from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.value_objects import ReadStatusId, RecordId
from shared.domain.value_objects import UserId


@dataclass
class ReadStatus:
    """Tracks when a user last viewed a Record.

    Not an aggregate root. Used to determine unread status by comparing
    last_viewed_at against Record.latest_activity_at.
    """

    id: ReadStatusId
    record_id: RecordId
    user_id: UserId
    _last_viewed_at: datetime

    @property
    def last_viewed_at(self) -> datetime:
        return self._last_viewed_at

    @staticmethod
    def create(
        *,
        record_id: RecordId,
        user_id: UserId,
        now: datetime | None = None,
    ) -> ReadStatus:
        """Create a new ReadStatus with last_viewed_at set to now."""
        ts = now or datetime.now(UTC)
        return ReadStatus(
            id=ReadStatusId.generate(),
            record_id=record_id,
            user_id=user_id,
            _last_viewed_at=ts,
        )

    def mark_viewed(self, now: datetime) -> None:
        """Update the last viewed timestamp."""
        self._last_viewed_at = now
