from datetime import datetime

import pytest

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.domain.events import (
    MemoUpdated,
    RecordCreated,
    RecordDraftSaved,
    RecordPublished,
    ViewersChanged,
)
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordStatus
from shared.domain.value_objects import UserId


def _make_record(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    schedule_id: ScheduleId | None = None,
    now: datetime | None = None,
) -> Record:
    """Helper to create a record with sensible defaults."""
    return Record.create(
        organizer_id=organizer_id or UserId.generate(),
        counterpart_id=counterpart_id or UserId.generate(),
        conducted_at=datetime(2026, 3, 20, 10, 0),
        schedule_id=schedule_id,
        now=now or datetime(2026, 3, 20, 10, 30),
    )


class TestRecordCreate:
    def test_creates_draft_with_empty_memo(self) -> None:
        record = _make_record()
        assert record.status == RecordStatus.DRAFT
        assert record.memo == Memo("")

    def test_creates_without_schedule_id(self) -> None:
        record = _make_record()
        assert record.schedule_id is None

    def test_creates_with_schedule_id(self) -> None:
        schedule_id = ScheduleId.generate()
        record = _make_record(schedule_id=schedule_id)
        assert record.schedule_id == schedule_id

    def test_emits_record_created_event(self) -> None:
        record = _make_record()
        events = record.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, RecordCreated)
        assert event.record_id == record.id
        assert event.organizer_id == record.organizer_id

    def test_sets_timestamps(self) -> None:
        now = datetime(2026, 3, 20, 10, 30)
        record = _make_record(now=now)
        assert record.created_at == now
        assert record.updated_at == now

    def test_collect_events_clears_list(self) -> None:
        record = _make_record()
        events = record.collect_events()
        assert len(events) == 1
        assert record.collect_events() == []


class TestRecordUpdateMemo:
    def test_organizer_can_update_memo(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.update_memo(memo=Memo("Discussion notes"), actor_id=organizer, now=now)

        assert record.memo == Memo("Discussion notes")
        assert record.updated_at == now

    def test_non_organizer_cannot_update_memo(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        record = _make_record(organizer_id=organizer)

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            record.update_memo(
                memo=Memo("hack"), actor_id=other, now=datetime(2026, 3, 20, 11, 0)
            )

    def test_cannot_update_memo_when_published(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        with pytest.raises(RecordAlreadyPublishedError):
            record.update_memo(
                memo=Memo("late edit"),
                actor_id=organizer,
                now=datetime(2026, 3, 20, 11, 0),
            )

    def test_emits_memo_updated_event(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.collect_events()  # clear creation event
        now = datetime(2026, 3, 20, 11, 0)

        record.update_memo(memo=Memo("Updated"), actor_id=organizer, now=now)

        events = record.collect_events()
        memo_events = [e for e in events if isinstance(e, MemoUpdated)]
        assert len(memo_events) == 1
        assert memo_events[0].record_id == record.id
        assert memo_events[0].updated_at == now


class TestRecordSaveDraft:
    def test_organizer_can_save_draft(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.save_draft(actor_id=organizer, now=now)

        assert record.updated_at == now

    def test_non_organizer_cannot_save_draft(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        record = _make_record(organizer_id=organizer)

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            record.save_draft(actor_id=other, now=datetime(2026, 3, 20, 11, 0))

    def test_cannot_save_draft_when_published(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        with pytest.raises(RecordAlreadyPublishedError):
            record.save_draft(actor_id=organizer, now=datetime(2026, 3, 20, 11, 0))

    def test_emits_record_draft_saved_event(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.collect_events()  # clear creation event
        now = datetime(2026, 3, 20, 11, 0)

        record.save_draft(actor_id=organizer, now=now)

        events = record.collect_events()
        draft_events = [e for e in events if isinstance(e, RecordDraftSaved)]
        assert len(draft_events) == 1
        assert draft_events[0].saved_at == now


class TestRecordPublish:
    def test_organizer_can_publish(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.publish(actor_id=organizer, now=now)

        assert record.status == RecordStatus.PUBLISHED
        assert record.updated_at == now

    def test_non_organizer_cannot_publish(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        record = _make_record(organizer_id=organizer)

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            record.publish(actor_id=other, now=datetime(2026, 3, 20, 11, 0))

    def test_cannot_publish_twice(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        with pytest.raises(RecordAlreadyPublishedError):
            record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 11, 0))

    def test_emits_record_published_event(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.collect_events()  # clear creation event
        now = datetime(2026, 3, 20, 11, 0)

        record.publish(actor_id=organizer, now=now)

        events = record.collect_events()
        pub_events = [e for e in events if isinstance(e, RecordPublished)]
        assert len(pub_events) == 1
        assert pub_events[0].published_at == now


class TestRecordVisibility:
    def test_draft_visible_to_organizer(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)

        assert record.is_visible_to(organizer) is True

    def test_draft_not_visible_to_counterpart(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)

        assert record.is_visible_to(counterpart) is False

    def test_draft_not_visible_to_other(self) -> None:
        record = _make_record()
        other = UserId.generate()

        assert record.is_visible_to(other) is False

    def test_published_visible_to_organizer(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        assert record.is_visible_to(organizer) is True

    def test_published_visible_to_counterpart(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        assert record.is_visible_to(counterpart) is True

    def test_published_visible_to_viewer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.set_viewers(
            viewer_ids=[viewer],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 10, 40),
        )
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))

        assert record.is_visible_to(viewer) is True

    def test_published_not_visible_to_non_viewer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 20, 10, 45))
        other = UserId.generate()

        assert record.is_visible_to(other) is False


class TestRecordViewers:
    def test_organizer_can_set_viewers(self) -> None:
        organizer = UserId.generate()
        viewer1 = UserId.generate()
        viewer2 = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.set_viewers(viewer_ids=[viewer1, viewer2], actor_id=organizer, now=now)

        assert viewer1 in record.viewers
        assert viewer2 in record.viewers
        assert len(record.viewers) == 2

    def test_non_organizer_cannot_set_viewers(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        record = _make_record(organizer_id=organizer)

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            record.set_viewers(
                viewer_ids=[UserId.generate()],
                actor_id=other,
                now=datetime(2026, 3, 20, 11, 0),
            )

    def test_excludes_organizer_from_viewers(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)

        record.set_viewers(
            viewer_ids=[organizer],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )

        assert record.viewers == []

    def test_excludes_counterpart_from_viewers(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record(organizer_id=organizer, counterpart_id=counterpart)

        record.set_viewers(
            viewer_ids=[counterpart],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )

        assert record.viewers == []

    def test_deduplicates_viewers(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_record(organizer_id=organizer)

        record.set_viewers(
            viewer_ids=[viewer, viewer, viewer],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )

        assert record.viewers == [viewer]

    def test_emits_viewers_changed_event(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.collect_events()  # clear creation event
        now = datetime(2026, 3, 20, 11, 0)

        record.set_viewers(viewer_ids=[viewer], actor_id=organizer, now=now)

        events = record.collect_events()
        viewer_events = [e for e in events if isinstance(e, ViewersChanged)]
        assert len(viewer_events) == 1
        assert viewer_events[0].record_id == record.id
        assert viewer_events[0].viewer_ids == (viewer,)
        assert viewer_events[0].changed_at == now

    def test_updates_timestamp(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.set_viewers(viewer_ids=[], actor_id=organizer, now=now)

        assert record.updated_at == now

    def test_viewers_property_returns_copy(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.set_viewers(
            viewer_ids=[viewer],
            actor_id=organizer,
            now=datetime(2026, 3, 20, 11, 0),
        )

        returned = record.viewers
        returned.append(UserId.generate())

        assert len(record.viewers) == 1
