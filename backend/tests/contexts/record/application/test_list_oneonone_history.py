"""Tests for ListOneOnOneHistoryQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.record.application.list_oneonone_history import (
    InvalidPaginationError,
    ListOneOnOneHistoryInput,
    ListOneOnOneHistoryOutput,
    ListOneOnOneHistoryQueryService,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import InMemoryRecordRepository


def _make_published_record(
    *,
    organizer: UserId,
    counterpart: UserId,
    conducted_at: datetime | None = None,
    memo: str = "",
    viewers: list[UserId] | None = None,
    now: datetime | None = None,
) -> Record:
    """Create a published Record for testing."""
    ts = now or datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=conducted_at or ts,
        now=ts,
    )
    if memo:
        record.update_memo(memo=Memo(memo), actor_id=organizer, now=ts)
    if viewers:
        record.set_viewers(viewer_ids=viewers, actor_id=organizer, now=ts)
    record.publish(actor_id=organizer, now=ts)
    record.collect_events()
    return record


def _build_service(
    *,
    record_repo: InMemoryRecordRepository | None = None,
) -> tuple[ListOneOnOneHistoryQueryService, InMemoryRecordRepository]:
    rr = record_repo or InMemoryRecordRepository()
    svc = ListOneOnOneHistoryQueryService(record_repository=rr)
    return svc, rr


class TestListOneOnOneHistory:
    """Tests for successful history retrieval."""

    async def test_returns_published_records_for_pair(self) -> None:
        """Basic retrieval of published records for a pair."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert isinstance(output, ListOneOnOneHistoryOutput)
        assert len(output.items) == 1
        assert output.total_count == 1
        assert output.items[0].record_id == record.id
        assert output.items[0].organizer_id == organizer
        assert output.items[0].counterpart_id == counterpart

    async def test_excludes_draft_records(self) -> None:
        """Draft records are not included in history."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        published = _make_published_record(organizer=organizer, counterpart=counterpart)
        draft = Record.create(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
        )
        draft.collect_events()
        assert draft.status == RecordStatus.DRAFT

        svc, rr = _build_service()
        await rr.save(published)
        await rr.save(draft)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 1
        assert len(output.items) == 1

    async def test_ordered_by_conducted_at_descending(self) -> None:
        """Records are returned newest-first by conducted_at."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        old_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            memo="old",
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        new_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            memo="new",
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr = _build_service()
        # Save in wrong order to verify sorting
        await rr.save(old_record)
        await rr.save(new_record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items) == 2
        assert output.items[0].memo_excerpt == "new"
        assert output.items[1].memo_excerpt == "old"

    async def test_memo_excerpt_truncated(self) -> None:
        """Memo excerpt is truncated to 100 characters."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        long_memo = "a" * 200
        record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            memo=long_memo,
        )

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert len(output.items[0].memo_excerpt) == 100

    async def test_memo_excerpt_short_memo_not_padded(self) -> None:
        """Short memos are returned as-is without padding."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            memo="short",
        )

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.items[0].memo_excerpt == "short"

    async def test_includes_schedule_id(self) -> None:
        """Schedule ID is included when the record was created from a schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        # Post-hoc records have no schedule_id
        assert output.items[0].schedule_id is None

    async def test_returns_empty_when_no_records(self) -> None:
        """Returns empty list and zero count when no matching records exist."""
        svc, _rr = _build_service()

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=UserId.generate(),
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
            )
        )

        assert output.items == []
        assert output.total_count == 0

    async def test_excludes_records_for_different_pair(self) -> None:
        """Records for a different pair are not returned."""
        organizer = UserId.generate()
        counterpart_a = UserId.generate()
        counterpart_b = UserId.generate()

        record_a = _make_published_record(
            organizer=organizer, counterpart=counterpart_a
        )
        record_b = _make_published_record(
            organizer=organizer, counterpart=counterpart_b
        )

        svc, rr = _build_service()
        await rr.save(record_a)
        await rr.save(record_b)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart_a,
            )
        )

        assert output.total_count == 1
        assert output.items[0].counterpart_id == counterpart_a


class TestListOneOnOneHistoryPagination:
    """Tests for offset-based pagination."""

    async def test_offset_skips_records(self) -> None:
        """Offset skips the first N records."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        svc, rr = _build_service()
        for i in range(5):
            record = _make_published_record(
                organizer=organizer,
                counterpart=counterpart,
                conducted_at=datetime(2026, 1, 1 + i, 10, 0, tzinfo=UTC),
                memo=f"record-{i}",
                now=datetime(2026, 1, 1 + i, 10, 0, tzinfo=UTC),
            )
            await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
                offset=2,
                limit=2,
            )
        )

        assert output.total_count == 5
        assert len(output.items) == 2
        # Descending order: records 4,3,2,1,0 -> offset 2 gives records 2,1
        assert output.items[0].memo_excerpt == "record-2"
        assert output.items[1].memo_excerpt == "record-1"

    async def test_limit_restricts_results(self) -> None:
        """Limit caps the number of returned records."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        svc, rr = _build_service()
        for i in range(5):
            record = _make_published_record(
                organizer=organizer,
                counterpart=counterpart,
                conducted_at=datetime(2026, 1, 1 + i, 10, 0, tzinfo=UTC),
                now=datetime(2026, 1, 1 + i, 10, 0, tzinfo=UTC),
            )
            await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
                limit=3,
            )
        )

        assert output.total_count == 5
        assert len(output.items) == 3

    async def test_total_count_consistent_with_visibility(self) -> None:
        """total_count matches the number of visible records, not all records."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()

        # Record visible to viewer
        visible_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            viewers=[viewer],
            conducted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        # Record NOT visible to viewer
        invisible_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr = _build_service()
        await rr.save(visible_record)
        await rr.save(invisible_record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=viewer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 1
        assert len(output.items) == 1

    async def test_default_offset_and_limit(self) -> None:
        """Default offset is 0 and default limit is 20."""
        input_dto = ListOneOnOneHistoryInput(
            actor_id=UserId.generate(),
            organizer_id=UserId.generate(),
            counterpart_id=UserId.generate(),
        )
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestListOneOnOneHistoryVisibility:
    """Tests for viewer-based visibility filtering."""

    async def test_organizer_sees_all_published(self) -> None:
        """The organizer can see all published records for the pair."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 1

    async def test_counterpart_sees_all_published(self) -> None:
        """The counterpart can see all published records for the pair."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=counterpart,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 1

    async def test_viewer_sees_only_records_with_viewer_access(self) -> None:
        """A viewer only sees records where they are in the viewers list."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()

        record_with_viewer = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            viewers=[viewer],
            conducted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        record_without_viewer = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr = _build_service()
        await rr.save(record_with_viewer)
        await rr.save(record_without_viewer)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=viewer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 1
        assert output.items[0].record_id == record_with_viewer.id

    async def test_outsider_sees_nothing(self) -> None:
        """A user not in organizer/counterpart/viewers sees nothing."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()

        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(record)

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=outsider,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output.total_count == 0
        assert output.items == []


class TestListOneOnOneHistoryValidation:
    """Tests for input validation."""

    async def test_negative_offset_raises(self) -> None:
        """Negative offset is rejected."""
        svc, _rr = _build_service()

        with pytest.raises(InvalidPaginationError):
            await svc.execute(
                ListOneOnOneHistoryInput(
                    actor_id=UserId.generate(),
                    organizer_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    offset=-1,
                )
            )

    async def test_zero_limit_raises(self) -> None:
        """limit=0 is rejected."""
        svc, _rr = _build_service()

        with pytest.raises(InvalidPaginationError):
            await svc.execute(
                ListOneOnOneHistoryInput(
                    actor_id=UserId.generate(),
                    organizer_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    limit=0,
                )
            )

    async def test_limit_exceeds_max_raises(self) -> None:
        """limit above 200 is rejected."""
        svc, _rr = _build_service()

        with pytest.raises(InvalidPaginationError):
            await svc.execute(
                ListOneOnOneHistoryInput(
                    actor_id=UserId.generate(),
                    organizer_id=UserId.generate(),
                    counterpart_id=UserId.generate(),
                    limit=201,
                )
            )

    async def test_limit_at_max_is_accepted(self) -> None:
        """limit=200 is valid (boundary)."""
        svc, _rr = _build_service()

        output = await svc.execute(
            ListOneOnOneHistoryInput(
                actor_id=UserId.generate(),
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
                limit=200,
            )
        )

        assert output.items == []
        assert output.total_count == 0
