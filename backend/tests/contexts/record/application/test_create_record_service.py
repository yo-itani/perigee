"""Tests for CreateRecordService."""

from __future__ import annotations

from datetime import datetime
from types import TracebackType

import pytest

from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.application.create_record_service import CreateRecordService
from contexts.record.domain.events import RecordCreated
from contexts.record.domain.record import Record
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import RecordId, RecordStatus
from foundation.application.unit_of_work import UnitOfWork
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class StubUnitOfWork(UnitOfWork):
    """In-memory UoW that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> StubUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class InMemoryRecordRepository(RecordRepository):
    """In-memory record repository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[RecordId, Record] = {}

    async def get_by_id(self, entity_id: RecordId) -> Record | None:
        return self._store.get(entity_id)

    async def save(self, entity: Record) -> None:
        self._store[entity.id] = entity

    @property
    def records(self) -> dict[RecordId, Record]:
        return dict(self._store)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateRecordFromSchedule:
    """Schedule-based record creation (use case 1)."""

    @pytest.fixture
    def uow(self) -> StubUnitOfWork:
        return StubUnitOfWork()

    @pytest.fixture
    def repo(self) -> InMemoryRecordRepository:
        return InMemoryRecordRepository()

    @pytest.fixture
    def dispatcher(self) -> InMemoryEventDispatcher:
        return InMemoryEventDispatcher()

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryRecordRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateRecordService:
        return CreateRecordService(
            uow=uow,
            record_repo=repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_record_in_draft_status(
        self,
        service: CreateRecordService,
        repo: InMemoryRecordRepository,
    ) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule_id = ScheduleId.generate()
        conducted_at = datetime(2026, 3, 20, 10, 0)

        record_id = await service.execute(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=conducted_at,
            schedule_id=schedule_id,
        )

        record = await repo.get_by_id(record_id)
        assert record is not None
        assert record.status == RecordStatus.DRAFT

    async def test_links_schedule_id(
        self,
        service: CreateRecordService,
        repo: InMemoryRecordRepository,
    ) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule_id = ScheduleId.generate()
        conducted_at = datetime(2026, 3, 20, 10, 0)

        record_id = await service.execute(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=conducted_at,
            schedule_id=schedule_id,
        )

        record = await repo.get_by_id(record_id)
        assert record is not None
        assert record.schedule_id == schedule_id

    async def test_sets_conducted_at(
        self,
        service: CreateRecordService,
        repo: InMemoryRecordRepository,
    ) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        conducted_at = datetime(2026, 3, 20, 10, 0)

        record_id = await service.execute(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=conducted_at,
        )

        record = await repo.get_by_id(record_id)
        assert record is not None
        assert record.conducted_at == conducted_at

    async def test_commits_via_uow(
        self,
        service: CreateRecordService,
        uow: StubUnitOfWork,
    ) -> None:
        await service.execute(
            organizer_id=UserId.generate(),
            counterpart_id=UserId.generate(),
            conducted_at=datetime(2026, 3, 20, 10, 0),
        )

        assert uow.committed is True

    async def test_dispatches_record_created_event(
        self,
        service: CreateRecordService,
    ) -> None:
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        # Re-create service with a dispatcher that captures events
        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(RecordCreated, capture_handler)  # type: ignore[arg-type]
        service_with_handler = CreateRecordService(
            uow=service._uow,
            record_repo=service._record_repo,
            event_dispatcher=dispatcher,
        )

        await service_with_handler.execute(
            organizer_id=UserId.generate(),
            counterpart_id=UserId.generate(),
            conducted_at=datetime(2026, 3, 20, 10, 0),
        )

        assert len(dispatched_events) == 1
        assert isinstance(dispatched_events[0], RecordCreated)


class TestCreatePostHocRecord:
    """Post-hoc record creation without schedule (Pattern C)."""

    @pytest.fixture
    def uow(self) -> StubUnitOfWork:
        return StubUnitOfWork()

    @pytest.fixture
    def repo(self) -> InMemoryRecordRepository:
        return InMemoryRecordRepository()

    @pytest.fixture
    def dispatcher(self) -> InMemoryEventDispatcher:
        return InMemoryEventDispatcher()

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        repo: InMemoryRecordRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateRecordService:
        return CreateRecordService(
            uow=uow,
            record_repo=repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_record_without_schedule_id(
        self,
        service: CreateRecordService,
        repo: InMemoryRecordRepository,
    ) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        conducted_at = datetime(2026, 3, 20, 10, 0)

        record_id = await service.execute(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=conducted_at,
        )

        record = await repo.get_by_id(record_id)
        assert record is not None
        assert record.schedule_id is None
        assert record.status == RecordStatus.DRAFT

    async def test_preserves_organizer_and_counterpart(
        self,
        service: CreateRecordService,
        repo: InMemoryRecordRepository,
    ) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()

        record_id = await service.execute(
            organizer_id=organizer,
            counterpart_id=counterpart,
            conducted_at=datetime(2026, 3, 20, 10, 0),
        )

        record = await repo.get_by_id(record_id)
        assert record is not None
        assert record.organizer_id == organizer
        assert record.counterpart_id == counterpart

    async def test_dispatches_event_with_null_schedule_id(
        self,
        service: CreateRecordService,
    ) -> None:
        dispatched_events: list[object] = []

        async def capture_handler(event: object) -> None:
            dispatched_events.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(RecordCreated, capture_handler)  # type: ignore[arg-type]
        service_with_handler = CreateRecordService(
            uow=service._uow,
            record_repo=service._record_repo,
            event_dispatcher=dispatcher,
        )

        await service_with_handler.execute(
            organizer_id=UserId.generate(),
            counterpart_id=UserId.generate(),
            conducted_at=datetime(2026, 3, 20, 10, 0),
        )

        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, RecordCreated)
        assert event.schedule_id is None
