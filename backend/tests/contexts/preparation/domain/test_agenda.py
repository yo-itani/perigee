from datetime import datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.comment_body import CommentBody
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)
_DEFAULT_TOPIC = Topic("Discuss project status")


def _make_agenda(
    *,
    schedule_id: ScheduleId | None = None,
    topic: Topic = _DEFAULT_TOPIC,
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
        assert agenda.topic == Topic("Discuss project status")
        assert agenda.comments == []
        assert agenda.created_at == _NOW

    def test_assigns_unique_id(self) -> None:
        a1 = _make_agenda()
        a2 = _make_agenda()
        assert a1.id != a2.id

    def test_topic_is_stored_as_given(self) -> None:
        agenda = _make_agenda(topic=Topic("padded"))
        assert agenda.topic == Topic("padded")


class TestAgendaComment:
    def test_add_comment(self) -> None:
        agenda = _make_agenda()
        author = UserId.generate()

        comment = agenda.add_comment(
            author_id=author,
            body=CommentBody("Let's focus on timeline"),
            now=_LATER,
        )

        assert len(agenda.comments) == 1
        assert comment.author_id == author
        assert comment.body == CommentBody("Let's focus on timeline")
        assert comment.agenda_id == agenda.id

    def test_multiple_comments(self) -> None:
        agenda = _make_agenda()
        user1 = UserId.generate()
        user2 = UserId.generate()

        agenda.add_comment(author_id=user1, body=CommentBody("Comment 1"), now=_LATER)
        agenda.add_comment(author_id=user2, body=CommentBody("Comment 2"), now=_LATER)

        assert len(agenda.comments) == 2

    def test_find_comment(self) -> None:
        agenda = _make_agenda()
        author = UserId.generate()
        comment = agenda.add_comment(
            author_id=author, body=CommentBody("Some comment"), now=_LATER
        )

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

    def test_comment_body_is_stored_as_given(self) -> None:
        agenda = _make_agenda()
        comment = agenda.add_comment(
            author_id=UserId.generate(),
            body=CommentBody("hello"),
            now=_LATER,
        )
        assert comment.body == CommentBody("hello")
