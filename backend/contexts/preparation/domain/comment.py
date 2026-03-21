from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.value_objects import AgendaId, CommentId
from shared.domain.value_objects import UserId


@dataclass
class Comment:
    """Child entity of Agenda representing a comment on an agenda topic.

    Both organizer and counterpart can add comments.
    Comments are always public (no private comments).
    """

    id: CommentId
    agenda_id: AgendaId
    author_id: UserId
    body: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        agenda_id: AgendaId,
        author_id: UserId,
        body: str,
        now: datetime | None = None,
    ) -> Comment:
        """Factory method to create a new comment."""
        ts = now or datetime.now(UTC)
        return Comment(
            id=CommentId.generate(),
            agenda_id=agenda_id,
            author_id=author_id,
            body=body,
            created_at=ts,
        )
