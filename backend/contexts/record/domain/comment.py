from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.events import CommentAdded
from contexts.record.domain.value_objects import CommentId, RecordId
from shared.domain.value_objects import UserId

type _CommentEvent = CommentAdded


@dataclass
class Comment:
    """Aggregate root: a comment on a published record.

    Comments can be made by organizer, counterpart, or viewers.
    Authorization (whether the actor is allowed to comment) is
    the responsibility of the application layer, not the domain.
    """

    id: CommentId
    record_id: RecordId
    author_id: UserId
    body: CommentBody
    created_at: datetime
    _events: list[_CommentEvent] = field(default_factory=list, repr=False)

    @staticmethod
    def create(
        *,
        record_id: RecordId,
        author_id: UserId,
        body: CommentBody,
        now: datetime | None = None,
    ) -> Comment:
        """Create a new comment."""
        comment_id = CommentId.generate()
        ts = now or datetime.now(UTC)
        comment = Comment(
            id=comment_id,
            record_id=record_id,
            author_id=author_id,
            body=body,
            created_at=ts,
        )
        comment._events.append(
            CommentAdded(
                comment_id=comment_id,
                record_id=record_id,
                author_id=author_id,
                created_at=ts,
            )
        )
        return comment

    def collect_events(self) -> list[_CommentEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events
