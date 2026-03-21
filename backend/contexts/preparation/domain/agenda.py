from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.comment import Comment
from contexts.preparation.domain.value_objects import AgendaId, CommentId, ScheduleId
from shared.domain.value_objects import UserId


@dataclass
class Agenda:
    """Entity: an agenda topic attached to a Schedule.

    An agenda is a topic prepared before a 1-on-1 meeting.
    It can have a comment thread (both organizer and counterpart can comment).

    Agendas are created either:
    - Via ScheduleGroup bulk operations (expanded from AgendaTemplate)
    - Directly added to an individual Schedule

    Post-hoc records (pattern C) do not have agendas.
    """

    id: AgendaId
    schedule_id: ScheduleId
    topic: str
    added_by: UserId
    _comments: list[Comment]
    created_at: datetime

    @property
    def comments(self) -> list[Comment]:
        return list(self._comments)

    @staticmethod
    def create(
        *,
        schedule_id: ScheduleId,
        topic: str,
        added_by: UserId,
        now: datetime | None = None,
    ) -> Agenda:
        """Factory method to create a new agenda item."""
        ts = now or datetime.now(UTC)
        return Agenda(
            id=AgendaId.generate(),
            schedule_id=schedule_id,
            topic=topic,
            added_by=added_by,
            _comments=[],
            created_at=ts,
        )

    def add_comment(self, *, author_id: UserId, body: str, now: datetime) -> Comment:
        """Add a comment to this agenda topic.

        Both organizer and counterpart can comment (no restriction).
        """
        comment = Comment.create(
            agenda_id=self.id,
            author_id=author_id,
            body=body,
            now=now,
        )
        self._comments.append(comment)
        return comment

    def find_comment(self, comment_id: CommentId) -> Comment | None:
        """Find a comment by its ID."""
        for comment in self._comments:
            if comment.id == comment_id:
                return comment
        return None
