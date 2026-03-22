from datetime import datetime

import pytest

from contexts.record.domain.comment import Comment
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.events import CommentAdded
from contexts.record.domain.exceptions import InvalidCommentBodyError
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId


def _make_comment(
    *,
    record_id: RecordId | None = None,
    author_id: UserId | None = None,
    body: str = "Great discussion today!",
    now: datetime | None = None,
) -> Comment:
    """Helper to create a comment with sensible defaults."""
    return Comment.create(
        record_id=record_id or RecordId.generate(),
        author_id=author_id or UserId.generate(),
        body=body,
        now=now or datetime(2026, 3, 20, 11, 0),
    )


class TestCommentCreate:
    def test_creates_with_defaults(self) -> None:
        comment = _make_comment()
        assert comment.body == CommentBody("Great discussion today!")

    def test_sets_record_id_and_author_id(self) -> None:
        record_id = RecordId.generate()
        author_id = UserId.generate()
        comment = _make_comment(record_id=record_id, author_id=author_id)

        assert comment.record_id == record_id
        assert comment.author_id == author_id

    def test_sets_timestamp(self) -> None:
        now = datetime(2026, 3, 20, 11, 0)
        comment = _make_comment(now=now)
        assert comment.created_at == now

    def test_body_must_not_be_empty(self) -> None:
        with pytest.raises(InvalidCommentBodyError, match="must not be empty"):
            _make_comment(body="   ")

    def test_body_must_not_exceed_max_length(self) -> None:
        with pytest.raises(InvalidCommentBodyError, match="must not exceed"):
            _make_comment(body="a" * 2001)

    def test_body_strips_whitespace(self) -> None:
        comment = _make_comment(body="  some comment  ")
        assert comment.body.value == "some comment"

    def test_emits_comment_added_event(self) -> None:
        now = datetime(2026, 3, 20, 11, 0)
        comment = _make_comment(now=now)
        events = comment.collect_events()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommentAdded)
        assert event.comment_id == comment.id
        assert event.record_id == comment.record_id
        assert event.author_id == comment.author_id
        assert event.created_at == now

    def test_collect_events_clears_list(self) -> None:
        comment = _make_comment()
        events = comment.collect_events()
        assert len(events) == 1
        assert comment.collect_events() == []
