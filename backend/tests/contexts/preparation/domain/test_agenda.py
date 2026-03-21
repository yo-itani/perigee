from datetime import datetime

import pytest

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.exceptions import InvalidCommentBodyError
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_agenda(
    *,
    schedule_id: ScheduleId | None = None,
    topic: str = "Discuss project status",
    added_by: UserId | None = None,
    now: datetime = _NOW,
) -> Agenda:
    return Agenda.create(
        schedule_id=schedule_id or ScheduleId.generate(),
        topic=topic,
        added_by=added_by or UserId.generate(),
        now=now,
    )


class TestAgendaCreate:
    def test_creates_with_defaults(self) -> None:
        agenda = _make_agenda()
        assert agenda.topic == "Discuss project status"
        assert agenda.comments == []
        assert agenda.created_at == _NOW

    def test_assigns_unique_id(self) -> None:
        a1 = _make_agenda()
        a2 = _make_agenda()
        assert a1.id != a2.id


class TestAgendaComment:
    def test_add_comment(self) -> None:
        agenda = _make_agenda()
        author = UserId.generate()

        comment = agenda.add_comment(
            author_id=author,
            body="Let's focus on timeline",
            now=_LATER,
        )

        assert len(agenda.comments) == 1
        assert comment.author_id == author
        assert comment.body == "Let's focus on timeline"
        assert comment.agenda_id == agenda.id

    def test_multiple_comments(self) -> None:
        agenda = _make_agenda()
        user1 = UserId.generate()
        user2 = UserId.generate()

        agenda.add_comment(author_id=user1, body="Comment 1", now=_LATER)
        agenda.add_comment(author_id=user2, body="Comment 2", now=_LATER)

        assert len(agenda.comments) == 2

    def test_find_comment(self) -> None:
        agenda = _make_agenda()
        author = UserId.generate()
        comment = agenda.add_comment(author_id=author, body="Some comment", now=_LATER)

        found = agenda.find_comment(comment.id)
        assert found is not None
        assert found.id == comment.id

    def test_find_comment_not_found(self) -> None:
        from contexts.preparation.domain.value_objects import CommentId

        agenda = _make_agenda()
        found = agenda.find_comment(CommentId.generate())
        assert found is None

    def test_comments_returns_copy(self) -> None:
        agenda = _make_agenda()
        comments = agenda.comments
        assert comments is not agenda.comments  # different list instances

    def test_empty_comment_body_raises(self) -> None:
        agenda = _make_agenda()
        with pytest.raises(InvalidCommentBodyError, match="must not be empty"):
            agenda.add_comment(author_id=UserId.generate(), body="", now=_LATER)

    def test_whitespace_only_comment_body_raises(self) -> None:
        agenda = _make_agenda()
        with pytest.raises(InvalidCommentBodyError, match="must not be empty"):
            agenda.add_comment(author_id=UserId.generate(), body="   ", now=_LATER)

    def test_comment_body_exceeds_max_length_raises(self) -> None:
        agenda = _make_agenda()
        with pytest.raises(InvalidCommentBodyError, match="must not exceed"):
            agenda.add_comment(author_id=UserId.generate(), body="a" * 2001, now=_LATER)

    def test_comment_body_at_max_length_is_valid(self) -> None:
        agenda = _make_agenda()
        comment = agenda.add_comment(
            author_id=UserId.generate(), body="a" * 2000, now=_LATER
        )
        assert len(comment.body) == 2000

    def test_comment_body_strips_whitespace(self) -> None:
        agenda = _make_agenda()
        comment = agenda.add_comment(
            author_id=UserId.generate(), body="  hello  ", now=_LATER
        )
        assert comment.body == "hello"
