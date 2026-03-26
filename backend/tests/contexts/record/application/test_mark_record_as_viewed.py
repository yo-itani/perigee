"""Tests for MarkRecordAsViewedUseCase."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.record.application.mark_record_as_viewed import (
    MarkRecordAsViewedInput,
    MarkRecordAsViewedUseCase,
    RecordNotFoundError,
    RecordNotVisibleError,
)
from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.read_status_repository import ReadStatusRepository
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import ReadStatusId, RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryRecordRepository,
)


class InMemoryReadStatusRepository(ReadStatusRepository):
    """In-memory stub for ReadStatusRepository."""

    def __init__(self) -> None:
        self._statuses: dict[ReadStatusId, ReadStatus] = {}

    async def get_by_id(self, entity_id: ReadStatusId) -> ReadStatus | None:
        return self._statuses.get(entity_id)

    async def save(self, entity: ReadStatus) -> None:
        self._statuses[entity.id] = entity

    async def find_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> ReadStatus | None:
        for rs in self._statuses.values():
            if rs.record_id == record_id and rs.user_id == user_id:
                return rs
        return None

    async def delete_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> None:
        to_delete = [
            k
            for k, v in self._statuses.items()
            if v.record_id == record_id and v.user_id == user_id
        ]
        for k in to_delete:
            del self._statuses[k]

    @property
    def saved_statuses(self) -> list[ReadStatus]:
        return list(self._statuses.values())


def _make_published_record(
    organizer: UserId | None = None,
    counterpart: UserId | None = None,
    viewers: list[UserId] | None = None,
) -> Record:
    org = organizer or UserId.generate()
    cp = counterpart or UserId.generate()
    record = Record.create(
        organizer_id=org,
        counterpart_id=cp,
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )
    record.publish(actor_id=org, now=datetime(2026, 3, 25, 12, 0))
    if viewers:
        record.set_viewers(
            viewer_ids=viewers, actor_id=org, now=datetime(2026, 3, 25, 12, 0)
        )
    record.collect_events()
    return record


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
) -> tuple[
    MarkRecordAsViewedUseCase,
    InMemoryRecordRepository,
    InMemoryReadStatusRepository,
    FakeUnitOfWork,
]:
    rr = record_repo or InMemoryRecordRepository()
    rs = read_status_repo or InMemoryReadStatusRepository()
    u = uow or FakeUnitOfWork()
    uc = MarkRecordAsViewedUseCase(
        record_repository=rr,
        read_status_repository=rs,
        unit_of_work=u,
    )
    return uc, rr, rs, u


class TestMarkRecordAsViewed:
    """Tests for successful marking of a record as viewed."""

    async def test_creates_read_status_for_first_view(self) -> None:
        """When no ReadStatus exists, a new one is created."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)

        await uc.execute(
            MarkRecordAsViewedInput(record_id=record.id, actor_id=counterpart)
        )

        read_status = await rs.find_by_record_and_user(record.id, counterpart)
        assert read_status is not None
        assert read_status.record_id == record.id
        assert read_status.user_id == counterpart

    async def test_updates_existing_read_status(self) -> None:
        """When ReadStatus already exists, last_viewed_at is updated."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)

        # First view
        existing = ReadStatus.create(
            record_id=record.id,
            user_id=counterpart,
            now=datetime(2026, 3, 24, 10, 0, tzinfo=UTC),
        )
        await rs.save(existing)
        original_viewed_at = existing.last_viewed_at

        # Second view
        await uc.execute(
            MarkRecordAsViewedInput(record_id=record.id, actor_id=counterpart)
        )

        updated = await rs.find_by_record_and_user(record.id, counterpart)
        assert updated is not None
        assert updated.last_viewed_at > original_viewed_at

    async def test_organizer_can_mark_as_viewed(self) -> None:
        """Organizer has visibility and can mark published record as viewed."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)

        await uc.execute(
            MarkRecordAsViewedInput(record_id=record.id, actor_id=organizer)
        )

        read_status = await rs.find_by_record_and_user(record.id, organizer)
        assert read_status is not None

    async def test_viewer_can_mark_as_viewed(self) -> None:
        """An explicit viewer can mark the record as viewed."""
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer=organizer, viewers=[viewer])
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)

        await uc.execute(MarkRecordAsViewedInput(record_id=record.id, actor_id=viewer))

        read_status = await rs.find_by_record_and_user(record.id, viewer)
        assert read_status is not None

    async def test_organizer_can_view_draft(self) -> None:
        """Draft records are visible only to the organizer."""
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        record.collect_events()
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)

        await uc.execute(
            MarkRecordAsViewedInput(record_id=record.id, actor_id=organizer)
        )

        read_status = await rs.find_by_record_and_user(record.id, organizer)
        assert read_status is not None

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _rs, uow = _build_use_case()
        await rr.save(record)

        await uc.execute(
            MarkRecordAsViewedInput(record_id=record.id, actor_id=organizer)
        )

        assert uow.committed is True


class TestMarkRecordAsViewedErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _rs, _uow = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                MarkRecordAsViewedInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_has_no_visibility(self) -> None:
        """A user without visibility cannot mark the record as viewed."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _rs, _uow = _build_use_case()
        await rr.save(record)
        stranger = UserId.generate()

        with pytest.raises(RecordNotVisibleError):
            await uc.execute(
                MarkRecordAsViewedInput(record_id=record.id, actor_id=stranger)
            )

    async def test_counterpart_cannot_view_draft(self) -> None:
        """Draft records are not visible to the counterpart."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        record.collect_events()
        uc, rr, _rs, _uow = _build_use_case()
        await rr.save(record)

        with pytest.raises(RecordNotVisibleError):
            await uc.execute(
                MarkRecordAsViewedInput(record_id=record.id, actor_id=counterpart)
            )

    async def test_does_not_commit_on_record_not_found(self) -> None:
        uc, _rr, _rs, uow = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                MarkRecordAsViewedInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert uow.committed is False

    async def test_does_not_commit_on_visibility_error(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _rs, uow = _build_use_case()
        await rr.save(record)

        with pytest.raises(RecordNotVisibleError):
            await uc.execute(
                MarkRecordAsViewedInput(
                    record_id=record.id,
                    actor_id=UserId.generate(),
                )
            )

        assert uow.committed is False

    async def test_does_not_save_read_status_on_visibility_error(self) -> None:
        """No ReadStatus should be created when visibility check fails."""
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, rs, _uow = _build_use_case()
        await rr.save(record)
        stranger = UserId.generate()

        with pytest.raises(RecordNotVisibleError):
            await uc.execute(
                MarkRecordAsViewedInput(record_id=record.id, actor_id=stranger)
            )

        assert len(rs.saved_statuses) == 0
