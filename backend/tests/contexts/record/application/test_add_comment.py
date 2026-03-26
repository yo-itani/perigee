"""Tests for AddCommentUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.add_comment import (
    AddCommentInput,
    AddCommentOutput,
    AddCommentUseCase,
    RecordNotFoundError,
)
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.events import RecordCommentAdded
from contexts.record.domain.exceptions import (
    RecordNotPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryCommentRepository,
    InMemoryReadStatusRepository,
    InMemoryRecordRepository,
    SpyEventDispatcher,
)


def _make_published_record(
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
    viewer_ids: list[UserId] | None = None,
) -> Record:
    org = organizer or UserId.generate()
    cp = counterpart or UserId.generate()
    record = Record.create(
        organizer_id=org,
        counterpart_id=cp,
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )
    record.publish(actor_id=org, now=datetime(2026, 3, 25, 11, 0))
    if viewer_ids:
        record.set_viewers(
            viewer_ids=viewer_ids,
            actor_id=org,
            now=datetime(2026, 3, 25, 11, 0),
        )
    record.collect_events()  # clear creation/publish events
    return record


def _make_draft_record(
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
) -> Record:
    record = Record.create(
        organizer_id=organizer or UserId.generate(),
        counterpart_id=counterpart or UserId.generate(),
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )
    record.collect_events()
    return record


def _build_use_case(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    comment_repo: InMemoryCommentRepository | None = None,
    read_status_repo: InMemoryReadStatusRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    AddCommentUseCase,
    InMemoryRecordRepository,
    InMemoryCommentRepository,
    InMemoryReadStatusRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    cr = comment_repo or InMemoryCommentRepository()
    rs = read_status_repo or InMemoryReadStatusRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = AddCommentUseCase(
        record_repository=rr,
        comment_repository=cr,
        read_status_repository=rs,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, cr, rs, u, ed


class TestAddComment:
    """Tests for successful comment addition."""

    async def test_organizer_can_add_comment(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Good session"),
            )
        )

        assert isinstance(output, AddCommentOutput)
        saved = cr.saved_comments
        assert len(saved) == 1
        assert saved[0].id == output.comment_id
        assert saved[0].record_id == record.id
        assert saved[0].author_id == organizer
        assert saved[0].body == CommentBody("Good session")

    async def test_counterpart_can_add_comment(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        uc, rr, cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=counterpart,
                body=CommentBody("Thanks for the feedback"),
            )
        )

        assert isinstance(output, AddCommentOutput)
        assert len(cr.saved_comments) == 1

    async def test_viewer_can_add_comment(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer=organizer, viewer_ids=[viewer])
        uc, rr, cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=viewer,
                body=CommentBody("Interesting points"),
            )
        )

        assert isinstance(output, AddCommentOutput)
        assert len(cr.saved_comments) == 1

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _cr, _rs, uow, _ed = _build_use_case()
        await rr.save(record)

        await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Comment"),
            )
        )

        assert uow.committed is True

    async def test_dispatches_record_comment_added_event(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _cr, _rs, _uow, ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Comment with event"),
            )
        )

        added_events = [
            e for e in ed.dispatched_events if isinstance(e, RecordCommentAdded)
        ]
        assert len(added_events) == 1
        event = added_events[0]
        assert event.comment_id == output.comment_id
        assert event.record_id == record.id
        assert event.author_id == organizer


class TestAddCommentErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _cr, _rs, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddCommentInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=CommentBody("Comment"),
                )
            )

    async def test_raises_when_record_is_draft(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        with pytest.raises(RecordNotPublishedError):
            await uc.execute(
                AddCommentInput(
                    record_id=record.id,
                    actor_id=organizer,
                    body=CommentBody("Comment on draft"),
                )
            )

    async def test_raises_when_user_has_no_access(self) -> None:
        record = _make_published_record()
        outsider = UserId.generate()
        uc, rr, _cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                AddCommentInput(
                    record_id=record.id,
                    actor_id=outsider,
                    body=CommentBody("Unauthorized comment"),
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, _cr, _rs, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddCommentInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=CommentBody("Comment"),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _cr, _rs, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddCommentInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=CommentBody("Comment"),
                )
            )

        assert ed.dispatched_events == []


class TestAddCommentLatestActivityAndAutoRead:
    """Tests for latest_activity_at update and author auto-read on comment."""

    async def test_updates_latest_activity_at_on_record(self) -> None:
        """Adding a comment should update Record.latest_activity_at."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        original_activity_at = record.latest_activity_at
        uc, rr, _cr, _rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("New comment"),
            )
        )

        saved_record = await rr.get_by_id(record.id)
        assert saved_record is not None
        assert saved_record.latest_activity_at is not None
        assert saved_record.latest_activity_at != original_activity_at

    async def test_auto_reads_commenter_when_no_prior_read_status(self) -> None:
        """Commenter should get a new ReadStatus with last_viewed_at = now."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _cr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Comment"),
            )
        )

        read_status = await rs.find_by_record_and_user(record.id, organizer)
        assert read_status is not None
        # last_viewed_at should equal latest_activity_at (same `now`)
        assert read_status.last_viewed_at == record.latest_activity_at

    async def test_auto_reads_commenter_when_prior_read_status_exists(self) -> None:
        """Existing ReadStatus should be updated, not duplicated."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _cr, rs, _uow, _ed = _build_use_case()
        await rr.save(record)

        # Pre-existing ReadStatus with an old timestamp
        old_read = ReadStatus.create(
            record_id=record.id,
            user_id=organizer,
            now=datetime(2026, 1, 1, 0, 0),
        )
        await rs.save(old_read)

        await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Another comment"),
            )
        )

        read_status = await rs.find_by_record_and_user(record.id, organizer)
        assert read_status is not None
        assert read_status.id == old_read.id  # same entity, not new
        assert read_status.last_viewed_at == record.latest_activity_at

    async def test_record_is_re_saved_in_same_transaction(self) -> None:
        """Record should be saved after notify_comment_added to persist latest_activity_at."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _cr, _rs, uow, _ed = _build_use_case()
        await rr.save(record)

        await uc.execute(
            AddCommentInput(
                record_id=record.id,
                actor_id=organizer,
                body=CommentBody("Trigger save"),
            )
        )

        assert uow.committed is True
        saved_record = await rr.get_by_id(record.id)
        assert saved_record is not None
        assert saved_record.latest_activity_at is not None
