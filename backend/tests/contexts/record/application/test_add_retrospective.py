"""Tests for AddRetrospectiveUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.add_retrospective import (
    AddRetrospectiveInput,
    AddRetrospectiveOutput,
    AddRetrospectiveUseCase,
    RecordNotFoundError,
)
from contexts.record.domain.events import RetrospectiveAdded
from contexts.record.domain.exceptions import (
    RecordNotPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record import Record
from contexts.record.domain.retrospective_body import RetrospectiveBody
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import (
    FakeUnitOfWork,
    InMemoryRecordRepository,
    InMemoryRetrospectiveRepository,
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
    retrospective_repo: InMemoryRetrospectiveRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    AddRetrospectiveUseCase,
    InMemoryRecordRepository,
    InMemoryRetrospectiveRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    retro_r = retrospective_repo or InMemoryRetrospectiveRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = AddRetrospectiveUseCase(
        record_repository=rr,
        retrospective_repository=retro_r,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, retro_r, u, ed


class TestAddRetrospective:
    """Tests for successful retrospective addition."""

    async def test_organizer_can_add_retrospective(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        uc, rr, retro_r, _uow, _ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddRetrospectiveInput(
                record_id=record.id,
                actor_id=organizer,
                body=RetrospectiveBody("The session went well"),
            )
        )

        assert isinstance(output, AddRetrospectiveOutput)
        saved = retro_r.saved_retrospectives
        assert len(saved) == 1
        assert saved[0].id == output.retrospective_id
        assert saved[0].record_id == record.id
        assert saved[0].author_id == organizer
        assert saved[0].body == RetrospectiveBody("The session went well")

    async def test_counterpart_can_add_retrospective(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_published_record(organizer=organizer, counterpart=counterpart)
        uc, rr, retro_r, _uow, _ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddRetrospectiveInput(
                record_id=record.id,
                actor_id=counterpart,
                body=RetrospectiveBody("Helpful discussion"),
            )
        )

        assert isinstance(output, AddRetrospectiveOutput)
        assert len(retro_r.saved_retrospectives) == 1

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _retro_r, uow, _ed = _build_use_case()
        await rr.save(record)

        await uc.execute(
            AddRetrospectiveInput(
                record_id=record.id,
                actor_id=organizer,
                body=RetrospectiveBody("Retrospective"),
            )
        )

        assert uow.committed is True

    async def test_dispatches_retrospective_added_event(self) -> None:
        organizer = UserId.generate()
        record = _make_published_record(organizer=organizer)
        uc, rr, _retro_r, _uow, ed = _build_use_case()
        await rr.save(record)

        output = await uc.execute(
            AddRetrospectiveInput(
                record_id=record.id,
                actor_id=organizer,
                body=RetrospectiveBody("Retrospective with event"),
            )
        )

        added_events = [
            e for e in ed.dispatched_events if isinstance(e, RetrospectiveAdded)
        ]
        assert len(added_events) == 1
        event = added_events[0]
        assert event.retrospective_id == output.retrospective_id
        assert event.record_id == record.id
        assert event.author_id == organizer


class TestAddRetrospectiveErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _retro_r, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=RetrospectiveBody("Retrospective"),
                )
            )

    async def test_raises_when_record_is_draft(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _retro_r, _uow, _ed = _build_use_case()
        await rr.save(record)

        with pytest.raises(RecordNotPublishedError):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=record.id,
                    actor_id=organizer,
                    body=RetrospectiveBody("Retrospective on draft"),
                )
            )

    async def test_raises_when_viewer_tries_to_add(self) -> None:
        organizer = UserId.generate()
        viewer = UserId.generate()
        record = _make_published_record(organizer=organizer, viewer_ids=[viewer])
        uc, rr, _retro_r, _uow, _ed = _build_use_case()
        await rr.save(record)

        with pytest.raises(
            UnauthorizedOperationError, match="organizer or counterpart"
        ):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=record.id,
                    actor_id=viewer,
                    body=RetrospectiveBody("Viewer retrospective"),
                )
            )

    async def test_raises_when_outsider_tries_to_add(self) -> None:
        record = _make_published_record()
        outsider = UserId.generate()
        uc, rr, _retro_r, _uow, _ed = _build_use_case()
        await rr.save(record)

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=record.id,
                    actor_id=outsider,
                    body=RetrospectiveBody("Outsider retrospective"),
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, _retro_r, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=RetrospectiveBody("Retrospective"),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _retro_r, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                AddRetrospectiveInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                    body=RetrospectiveBody("Retrospective"),
                )
            )

        assert ed.dispatched_events == []
