"""Tests for SaveDraftUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.save_draft import (
    RecordNotFoundError,
    SaveDraftInput,
    SaveDraftOutput,
    SaveDraftUseCase,
)
from contexts.record.domain.events import RecordDraftSaved, RecordPublished
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId, RecordStatus
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
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
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    SaveDraftUseCase,
    InMemoryRecordRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = SaveDraftUseCase(
        record_repository=rr,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, u, ed


class TestSaveDraft:
    """Tests for successful draft save."""

    async def test_saves_record_as_draft(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SaveDraftInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert isinstance(output, SaveDraftOutput)
        assert output.record_id == record.id
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert saved.status == RecordStatus.DRAFT

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SaveDraftInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert uow.committed is True

    async def test_dispatches_draft_saved_event_not_published(self) -> None:
        """Draft save should dispatch RecordDraftSaved, not RecordPublished."""
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _uow, ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SaveDraftInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        draft_events = [
            e for e in ed.dispatched_events if isinstance(e, RecordDraftSaved)
        ]
        publish_events = [
            e for e in ed.dispatched_events if isinstance(e, RecordPublished)
        ]
        assert len(draft_events) == 1
        assert draft_events[0].record_id == record.id
        assert draft_events[0].organizer_id == organizer
        assert len(publish_events) == 0

    async def test_draft_is_only_visible_to_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            SaveDraftInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert saved.is_visible_to(organizer) is True
        assert saved.is_visible_to(counterpart) is False
        assert saved.is_visible_to(UserId.generate()) is False


class TestSaveDraftErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SaveDraftInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                SaveDraftInput(
                    record_id=record.id,
                    actor_id=counterpart,
                )
            )

    async def test_raises_when_record_is_published(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        record.publish(actor_id=organizer, now=datetime(2026, 3, 25, 12, 0))
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(RecordAlreadyPublishedError):
            await uc.execute(
                SaveDraftInput(
                    record_id=record.id,
                    actor_id=organizer,
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SaveDraftInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SaveDraftInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert ed.dispatched_events == []
