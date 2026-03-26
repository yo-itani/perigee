"""Tests for ListDraftRecordsQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.application.list_draft_records import (
    ListDraftRecordsInput,
    ListDraftRecordsOutput,
    ListDraftRecordsQueryService,
)
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import InMemoryRecordRepository


def _make_draft_record(
    *,
    organizer: UserId,
    counterpart: UserId,
    memo: str = "",
    schedule_id: ScheduleId | None = None,
    now: datetime | None = None,
) -> Record:
    """Create a DRAFT Record for testing."""
    ts = now or datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=ts,
        schedule_id=schedule_id,
        now=ts,
    )
    if memo:
        record.update_memo(memo=Memo(memo), actor_id=organizer, now=ts)
    record.collect_events()
    return record


def _make_published_record(
    *,
    organizer: UserId,
    counterpart: UserId,
    now: datetime | None = None,
) -> Record:
    """Create a PUBLISHED Record for testing."""
    ts = now or datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=ts,
        now=ts,
    )
    record.publish(actor_id=organizer, now=ts)
    record.collect_events()
    return record


def _build_service(
    *,
    record_repo: InMemoryRecordRepository | None = None,
) -> tuple[ListDraftRecordsQueryService, InMemoryRecordRepository]:
    rr = record_repo or InMemoryRecordRepository()
    svc = ListDraftRecordsQueryService(record_repository=rr)
    return svc, rr


class TestListDraftRecords:
    """Tests for successful draft records retrieval."""

    async def test_returns_draft_records_for_organizer(self) -> None:
        """Basic retrieval of draft records owned by the actor."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        draft = _make_draft_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert isinstance(output, ListDraftRecordsOutput)
        assert len(output.items) == 1
        assert output.items[0].record_id == draft.id
        assert output.items[0].counterpart_id == counterpart

    async def test_excludes_published_records(self) -> None:
        """Published records are not included in draft list."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        draft = _make_draft_record(
            organizer=organizer,
            counterpart=counterpart,
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )
        published = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            now=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        )
        assert draft.status == RecordStatus.DRAFT
        assert published.status == RecordStatus.PUBLISHED

        svc, rr = _build_service()
        await rr.save(draft)
        await rr.save(published)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert len(output.items) == 1
        assert output.items[0].record_id == draft.id

    async def test_excludes_other_organizers_drafts(self) -> None:
        """Drafts belonging to other organizers are not returned."""
        organizer_a = UserId.generate()
        organizer_b = UserId.generate()
        counterpart = UserId.generate()

        draft_a = _make_draft_record(organizer=organizer_a, counterpart=counterpart)
        draft_b = _make_draft_record(organizer=organizer_b, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(draft_a)
        await rr.save(draft_b)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer_a))

        assert len(output.items) == 1
        assert output.items[0].record_id == draft_a.id

    async def test_ordered_by_created_at_descending(self) -> None:
        """Records are returned newest-first by created_at."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        old_draft = _make_draft_record(
            organizer=organizer,
            counterpart=counterpart,
            memo="old",
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        new_draft = _make_draft_record(
            organizer=organizer,
            counterpart=counterpart,
            memo="new",
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr = _build_service()
        # Save in wrong order to verify sorting
        await rr.save(old_draft)
        await rr.save(new_draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert len(output.items) == 2
        assert output.items[0].memo_excerpt == "new"
        assert output.items[1].memo_excerpt == "old"

    async def test_memo_excerpt_truncated_to_100_chars(self) -> None:
        """Memo excerpt is truncated to 100 characters."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        long_memo = "a" * 200
        draft = _make_draft_record(
            organizer=organizer, counterpart=counterpart, memo=long_memo
        )

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert len(output.items[0].memo_excerpt) == 100

    async def test_short_memo_not_padded(self) -> None:
        """Short memos are returned as-is without padding."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        draft = _make_draft_record(
            organizer=organizer, counterpart=counterpart, memo="short"
        )

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert output.items[0].memo_excerpt == "short"

    async def test_includes_created_at(self) -> None:
        """Output includes created_at timestamp."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        ts = datetime(2026, 3, 15, 14, 30, tzinfo=UTC)
        draft = _make_draft_record(organizer=organizer, counterpart=counterpart, now=ts)

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert output.items[0].created_at == ts

    async def test_includes_schedule_id_when_present(self) -> None:
        """Schedule ID is included when the record was created from a schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule_id = ScheduleId.generate()
        draft = _make_draft_record(
            organizer=organizer,
            counterpart=counterpart,
            schedule_id=schedule_id,
        )

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert output.items[0].schedule_id == schedule_id

    async def test_schedule_id_none_for_post_hoc_record(self) -> None:
        """Schedule ID is None for post-hoc records."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        draft = _make_draft_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=organizer))

        assert output.items[0].schedule_id is None

    async def test_returns_empty_when_no_drafts(self) -> None:
        """Returns empty list when no matching draft records exist."""
        svc, _rr = _build_service()

        output = await svc.execute(ListDraftRecordsInput(actor_id=UserId.generate()))

        assert output.items == []

    async def test_counterpart_cannot_see_organizer_drafts(self) -> None:
        """The counterpart of a draft record cannot see it."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        draft = _make_draft_record(organizer=organizer, counterpart=counterpart)

        svc, rr = _build_service()
        await rr.save(draft)

        output = await svc.execute(ListDraftRecordsInput(actor_id=counterpart))

        assert output.items == []
