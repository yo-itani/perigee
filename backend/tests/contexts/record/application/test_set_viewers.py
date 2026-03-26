"""Tests for SetViewersUseCase."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.record.application.set_viewers import (
    RecordNotFoundError,
    SetViewersInput,
    SetViewersOutput,
    SetViewersUseCase,
)
from contexts.record.domain.events import ViewersChanged
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryReadStatusRepository,
    InMemoryRecordRepository,
    SpyEventDispatcher,
)


def _make_draft_record(
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
) -> Record:
    return Record.create(
        organizer_id=organizer or UserId.generate(),
        counterpart_id=counterpart or UserId.generate(),
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )


def _build_use_case(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    read_status_repo: InMemoryReadStatusRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    SetViewersUseCase,
    InMemoryRecordRepository,
    InMemoryReadStatusRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    rs = read_status_repo or InMemoryReadStatusRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = SetViewersUseCase(
        record_repository=rr,
        read_status_repository=rs,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, rs, u, ed


class TestSetViewers:
    """Tests for successful viewer setting."""

    async def test_sets_viewers_on_draft_record(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        assert isinstance(output, SetViewersOutput)
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert viewer in saved.viewers

    async def test_sets_viewers_on_published_record(self) -> None:
        """Viewers can be changed after publication."""
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 25, 11, 0))
        uc, rr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        assert isinstance(output, SetViewersOutput)
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert viewer in saved.viewers

    async def test_deduplicates_organizer_and_counterpart(self) -> None:
        """Organizer and counterpart are excluded from the explicit viewers list."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[organizer, counterpart, viewer],
            )
        )

        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert saved.viewers == [viewer]

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _rs, uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[],
            )
        )

        assert uow.committed is True

    async def test_dispatches_viewers_changed_event(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _rs, _uow, ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        events = [e for e in ed.dispatched_events if isinstance(e, ViewersChanged)]
        assert len(events) == 1
        assert events[0].record_id == record.id
        assert viewer in events[0].viewer_ids


class TestSetViewersReadStatus:
    """Tests for ReadStatus management when viewers are added/removed."""

    async def test_creates_read_status_for_added_viewer(self) -> None:
        """When a viewer is added, a ReadStatus is created with last_viewed_at
        set to the current timestamp, so past events are treated as read."""
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        read_status = await rs.find_by_record_and_user(record.id, viewer)
        assert read_status is not None
        assert read_status.record_id == record.id
        assert read_status.user_id == viewer
        # last_viewed_at should be set (not None), representing the add timestamp
        assert read_status.last_viewed_at is not None

    async def test_deletes_read_status_for_removed_viewer(self) -> None:
        """When a viewer is removed, their ReadStatus is deleted."""
        organizer = UserId.generate()
        viewer_to_remove = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        # First, add the viewer
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer_to_remove],
            )
        )
        # Verify ReadStatus exists
        assert await rs.find_by_record_and_user(record.id, viewer_to_remove) is not None

        # Now remove the viewer by setting empty list
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[],
            )
        )

        # ReadStatus should be deleted
        assert await rs.find_by_record_and_user(record.id, viewer_to_remove) is None

    async def test_added_viewer_past_events_are_read(self) -> None:
        """When a viewer is added, their last_viewed_at is set to the add
        timestamp, so any latest_activity_at before that is considered read."""
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        # Publish the record so it has a latest_activity_at
        publish_time = datetime(2026, 3, 25, 11, 0, tzinfo=UTC)
        record.publish(actor_id=organizer, now=publish_time)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        read_status = await rs.find_by_record_and_user(record.id, viewer)
        assert read_status is not None
        # The viewer's last_viewed_at should be >= the publish time,
        # meaning the publication event is treated as read
        assert read_status.last_viewed_at >= publish_time

    async def test_viewer_replacement_manages_read_status(self) -> None:
        """Replacing one viewer with another creates ReadStatus for the new
        viewer and deletes it for the old viewer."""
        organizer = UserId.generate()
        old_viewer = UserId.generate()
        new_viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        # Set old_viewer
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[old_viewer],
            )
        )
        assert await rs.find_by_record_and_user(record.id, old_viewer) is not None

        # Replace with new_viewer
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[new_viewer],
            )
        )

        # Old viewer's ReadStatus should be deleted
        assert await rs.find_by_record_and_user(record.id, old_viewer) is None
        # New viewer's ReadStatus should exist
        assert await rs.find_by_record_and_user(record.id, new_viewer) is not None

    async def test_unchanged_viewer_keeps_read_status(self) -> None:
        """A viewer that remains in the list should not have their
        ReadStatus recreated or modified."""
        organizer = UserId.generate()
        kept_viewer = UserId.generate()
        added_viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        # Set kept_viewer
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[kept_viewer],
            )
        )
        original_status = await rs.find_by_record_and_user(record.id, kept_viewer)
        assert original_status is not None
        original_viewed_at = original_status.last_viewed_at

        # Add another viewer while keeping the first
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[kept_viewer, added_viewer],
            )
        )

        # The kept viewer's ReadStatus should still exist with same last_viewed_at
        kept_status = await rs.find_by_record_and_user(record.id, kept_viewer)
        assert kept_status is not None
        assert kept_status.last_viewed_at == original_viewed_at
        # The added viewer should have a new ReadStatus
        assert await rs.find_by_record_and_user(record.id, added_viewer) is not None

    async def test_no_read_status_changes_when_viewers_unchanged(self) -> None:
        """Setting the same viewers list should not create or delete ReadStatus."""
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        # Set viewer
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )
        statuses_count = len(rs.saved_statuses)

        # Set same viewer again
        await uc.execute(
            SetViewersInput(
                record_id=record.id,
                actor_id=organizer,
                viewer_ids=[viewer],
            )
        )

        # No new ReadStatus should be created
        assert len(rs.saved_statuses) == statuses_count


class TestSetViewersErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _rs, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SetViewersInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    viewer_ids=[],
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                SetViewersInput(
                    record_id=record.id,
                    actor_id=counterpart,
                    viewer_ids=[],
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, _rs, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SetViewersInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    viewer_ids=[],
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _rs, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SetViewersInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    viewer_ids=[],
                )
            )

        assert ed.dispatched_events == []
