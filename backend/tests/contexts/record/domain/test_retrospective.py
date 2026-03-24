from datetime import datetime

from contexts.record.domain.events import RetrospectiveAdded
from contexts.record.domain.retrospective import Retrospective
from contexts.record.domain.retrospective_body import RetrospectiveBody
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId

_DEFAULT_BODY = RetrospectiveBody("Good progress on goals.")


def _make_retrospective(
    *,
    record_id: RecordId | None = None,
    author_id: UserId | None = None,
    body: RetrospectiveBody = _DEFAULT_BODY,
    now: datetime | None = None,
) -> Retrospective:
    """Helper to create a retrospective with sensible defaults."""
    return Retrospective.create(
        record_id=record_id or RecordId.generate(),
        author_id=author_id or UserId.generate(),
        body=body,
        now=now or datetime(2026, 3, 20, 11, 0),
    )


class TestRetrospectiveCreate:
    def test_creates_with_defaults(self) -> None:
        retrospective = _make_retrospective()
        assert retrospective.body == RetrospectiveBody("Good progress on goals.")

    def test_sets_record_id_and_author_id(self) -> None:
        record_id = RecordId.generate()
        author_id = UserId.generate()
        retrospective = _make_retrospective(record_id=record_id, author_id=author_id)

        assert retrospective.record_id == record_id
        assert retrospective.author_id == author_id

    def test_sets_timestamp(self) -> None:
        now = datetime(2026, 3, 20, 11, 0)
        retrospective = _make_retrospective(now=now)
        assert retrospective.created_at == now

    def test_body_is_stored_as_given(self) -> None:
        retrospective = _make_retrospective(
            body=RetrospectiveBody("some retrospective")
        )
        assert retrospective.body == RetrospectiveBody("some retrospective")

    def test_emits_retrospective_added_event(self) -> None:
        now = datetime(2026, 3, 20, 11, 0)
        retrospective = _make_retrospective(now=now)
        events = retrospective.collect_events()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, RetrospectiveAdded)
        assert event.retrospective_id == retrospective.id
        assert event.record_id == retrospective.record_id
        assert event.author_id == retrospective.author_id
        assert event.occurred_at == now

    def test_collect_events_clears_list(self) -> None:
        retrospective = _make_retrospective()
        events = retrospective.collect_events()
        assert len(events) == 1
        assert retrospective.collect_events() == []
