"""Tests for GetLastSessionSummaryQueryService."""

from __future__ import annotations

from datetime import UTC, datetime

from contexts.record.application.get_last_session_summary import (
    GetLastSessionSummaryInput,
    GetLastSessionSummaryOutput,
    GetLastSessionSummaryQueryService,
)
from contexts.record.domain.action_item import ActionItem
from contexts.record.domain.memo import Memo
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ActionItemTitle, RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    InMemoryActionItemRepository,
    InMemoryRecordRepository,
)


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


def _make_action_item(
    *,
    counterpart: UserId,
    record_id: RecordId,
    organizer: UserId,
    title: str = "Follow up",
    now: datetime | None = None,
) -> ActionItem:
    item = ActionItem.create(
        counterpart_id=counterpart,
        record_id=record_id,
        title=ActionItemTitle(title),
        actor_id=organizer,
        organizer_id=organizer,
        now=now,
    )
    item.collect_events()
    return item


def _build_service(
    *,
    record_repo: InMemoryRecordRepository | None = None,
    action_item_repo: InMemoryActionItemRepository | None = None,
) -> tuple[
    GetLastSessionSummaryQueryService,
    InMemoryRecordRepository,
    InMemoryActionItemRepository,
]:
    rr = record_repo or InMemoryRecordRepository()
    air = action_item_repo or InMemoryActionItemRepository()
    svc = GetLastSessionSummaryQueryService(
        record_repository=rr,
        action_item_repository=air,
    )
    return svc, rr, air


class TestGetLastSessionSummary:
    """Tests for successful summary retrieval."""

    async def test_returns_latest_record_summary(self) -> None:
        """Returns the most recent published record for the pair."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        old_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            memo="old memo",
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        new_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            memo="new memo",
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr, _air = _build_service()
        await rr.save(old_record)
        await rr.save(new_record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert isinstance(output, GetLastSessionSummaryOutput)
        assert output.record_id == new_record.id
        assert output.conducted_at == datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        assert output.memo_excerpt == "new memo"

    async def test_returns_none_when_no_records(self) -> None:
        """Returns None when no matching record exists."""
        svc, _rr, _air = _build_service()

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=UserId.generate(),
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
            )
        )

        assert output is None

    async def test_memo_excerpt_truncated_to_200(self) -> None:
        """Memo excerpt in summary is truncated to 200 characters."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        long_memo = "x" * 300
        record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            memo=long_memo,
        )

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert len(output.memo_excerpt) == 200

    async def test_includes_all_action_items(self) -> None:
        """All action items (completed and pending) are included."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        pending = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Pending task",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )
        completed = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Done task",
            now=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
        )
        completed.complete(
            actor_id=counterpart,
            now=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        )
        completed.collect_events()

        svc, rr, air = _build_service()
        await rr.save(record)
        await air.save(pending)
        await air.save(completed)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert len(output.action_items) == 2

        # Verify completed status
        items_by_content = {ai.content: ai for ai in output.action_items}
        assert not items_by_content["Pending task"].is_completed
        assert items_by_content["Done task"].is_completed

    async def test_action_items_ordered_by_created_at_ascending(self) -> None:
        """Action items are returned oldest-first."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        item_old = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Old item",
            now=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        )
        item_new = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="New item",
            now=datetime(2026, 3, 1, 14, 0, tzinfo=UTC),
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        # Save in reverse order
        await air.save(item_new)
        await air.save(item_old)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert len(output.action_items) == 2
        assert output.action_items[0].content == "Old item"
        assert output.action_items[1].content == "New item"

    async def test_action_item_dto_fields(self) -> None:
        """Each action item DTO has the correct fields."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        item_ts = datetime(2026, 3, 1, 11, 30, tzinfo=UTC)
        item = _make_action_item(
            counterpart=counterpart,
            record_id=record.id,
            organizer=organizer,
            title="Check status",
            now=item_ts,
        )

        svc, rr, air = _build_service()
        await rr.save(record)
        await air.save(item)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert len(output.action_items) == 1
        ai_dto = output.action_items[0]
        assert ai_dto.action_item_id == item.id
        assert ai_dto.content == "Check status"
        assert ai_dto.is_completed is False
        assert ai_dto.created_at == item_ts

    async def test_no_action_items_returns_empty_list(self) -> None:
        """When the record has no action items, returns empty list."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert output.action_items == []


class TestGetLastSessionSummaryVisibility:
    """Tests for viewer-based visibility in summary."""

    async def test_counterpart_can_get_summary(self) -> None:
        """The counterpart can get the last session summary."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=counterpart,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert output.record_id == record.id

    async def test_viewer_gets_visible_record(self) -> None:
        """A viewer gets the latest record they can see."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()

        # Older record visible to viewer
        visible_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            viewers=[viewer],
            conducted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        # Newer record NOT visible to viewer
        _invisible_record = _make_published_record(
            organizer=organizer,
            counterpart=counterpart,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )

        svc, rr, _air = _build_service()
        await rr.save(visible_record)
        await rr.save(_invisible_record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=viewer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is not None
        assert output.record_id == visible_record.id

    async def test_outsider_gets_none(self) -> None:
        """A user not in organizer/counterpart/viewers gets None."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()

        record = _make_published_record(organizer=organizer, counterpart=counterpart)

        svc, rr, _air = _build_service()
        await rr.save(record)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=outsider,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is None

    async def test_excludes_draft_records(self) -> None:
        """Draft records are not returned even for organizer."""
        organizer = UserId.generate()
        counterpart = UserId.generate()

        draft = Record.create(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            now=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        )
        draft.collect_events()

        svc, rr, _air = _build_service()
        await rr.save(draft)

        output = await svc.execute(
            GetLastSessionSummaryInput(
                actor_id=organizer,
                organizer_id=organizer,
                counterpart_id=counterpart,
            )
        )

        assert output is None
