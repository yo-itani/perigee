from datetime import datetime

import pytest

from contexts.recording.domain.events import (
    MemoUpdated,
    RecordCreated,
    RecordDraftSaved,
)
from contexts.recording.domain.record import Record
from contexts.recording.domain.value_objects import RecordStatus
from shared.domain.value_objects import ScheduleId, UserId


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
        assert record.memo == ""

    def test_creates_without_schedule_id(self) -> None:
        record = _make_record()
        assert record.schedule_id is None

    def test_creates_with_schedule_id(self) -> None:
        schedule_id = ScheduleId.generate()
        record = _make_record(schedule_id=schedule_id)
        assert record.schedule_id == schedule_id

    def test_emits_record_created_event(self) -> None:
        record = _make_record()
        assert len(record.events) == 1
        event = record.events[0]
        assert isinstance(event, RecordCreated)
        assert event.record_id == record.id
        assert event.organizer_id == record.organizer_id

    def test_sets_timestamps(self) -> None:
        now = datetime(2026, 3, 20, 10, 30)
        record = _make_record(now=now)
        assert record.created_at == now
        assert record.updated_at == now


class TestRecordUpdateMemo:
    def test_organizer_can_update_memo(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.update_memo(memo="Discussion notes", actor_id=organizer, now=now)

        assert record.memo == "Discussion notes"
        assert record.updated_at == now

    def test_non_organizer_cannot_update_memo(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        record = _make_record(organizer_id=organizer)

        with pytest.raises(PermissionError, match="Only the organizer"):
            record.update_memo(
                memo="hack", actor_id=other, now=datetime(2026, 3, 20, 11, 0)
            )

    def test_emits_memo_updated_event(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.update_memo(memo="Updated", actor_id=organizer, now=now)

        memo_events = [e for e in record.events if isinstance(e, MemoUpdated)]
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

        with pytest.raises(PermissionError, match="Only the organizer"):
            record.save_draft(actor_id=other, now=datetime(2026, 3, 20, 11, 0))

    def test_cannot_save_draft_when_published(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        record.status = RecordStatus.PUBLISHED

        with pytest.raises(ValueError, match="not in draft status"):
            record.save_draft(actor_id=organizer, now=datetime(2026, 3, 20, 11, 0))

    def test_emits_record_draft_saved_event(self) -> None:
        organizer = UserId.generate()
        record = _make_record(organizer_id=organizer)
        now = datetime(2026, 3, 20, 11, 0)

        record.save_draft(actor_id=organizer, now=now)

        draft_events = [e for e in record.events if isinstance(e, RecordDraftSaved)]
        assert len(draft_events) == 1
        assert draft_events[0].saved_at == now


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

    def test_published_visible_to_anyone(self) -> None:
        record = _make_record()
        record.status = RecordStatus.PUBLISHED
        other = UserId.generate()

        assert record.is_visible_to(other) is True
