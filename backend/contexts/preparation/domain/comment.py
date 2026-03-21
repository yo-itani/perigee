from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.preparation.domain.exceptions import InvalidCommentBodyError
from contexts.preparation.domain.value_objects import AgendaId, CommentId
from shared.domain.value_objects import UserId

_COMMENT_BODY_MAX_LENGTH = 2000


@dataclass
class Comment:
    """Child entity of Agenda representing a comment on an agenda topic.

    Both organizer and counterpart can add comments.
    Comments are always public (no private comments).
    """

    _id: CommentId
    _agenda_id: AgendaId
    _author_id: UserId
    _body: str
    _created_at: datetime

    @property
    def id(self) -> CommentId:
        return self._id

    @property
    def agenda_id(self) -> AgendaId:
        return self._agenda_id

    @property
    def author_id(self) -> UserId:
        return self._author_id

    @property
    def body(self) -> str:
        return self._body

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @staticmethod
    def create(
        *,
        agenda_id: AgendaId,
        author_id: UserId,
        body: str,
        now: datetime | None = None,
    ) -> Comment:
        """Factory method to create a new comment.

        Raises:
            InvalidCommentBodyError: If body is empty or exceeds max length.
        """
        ts = now or datetime.now(UTC)
        validated_body = _validate_comment_body(body)
        return Comment(
            _id=CommentId.generate(),
            _agenda_id=agenda_id,
            _author_id=author_id,
            _body=validated_body,
            _created_at=ts,
        )


def _validate_comment_body(body: str) -> str:
    """Validate and normalize a comment body."""
    stripped = body.strip()
    if not stripped:
        raise InvalidCommentBodyError("Comment body must not be empty.")
    if len(stripped) > _COMMENT_BODY_MAX_LENGTH:
        raise InvalidCommentBodyError(
            f"Comment body must not exceed {_COMMENT_BODY_MAX_LENGTH} characters."
        )
    return stripped
