"""Tests for ConfirmAgendaUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.preparation.domain.value_objects import AgendaId
from contexts.record.application.confirm_agenda import (
    ConfirmAgendaInput,
    ConfirmAgendaOutput,
    ConfirmAgendaUseCase,
    RecordNotFoundError,
)
from contexts.record.domain.events import AgendaConfirmed
from contexts.record.domain.exceptions import (
    AgendaAlreadyConfirmedError,
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
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
    ConfirmAgendaUseCase,
    InMemoryRecordRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    rr = record_repo or InMemoryRecordRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = ConfirmAgendaUseCase(
        record_repository=rr,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, rr, u, ed


class TestConfirmAgenda:
    """Tests for successful agenda confirmation."""

    async def test_organizer_can_confirm_agenda(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        agenda_id = AgendaId.generate()
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id,
                agenda_id=agenda_id,
                actor_id=organizer,
            )
        )

        assert isinstance(output, ConfirmAgendaOutput)
        assert output.record_id == record.id
        assert output.agenda_id == agenda_id
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert agenda_id in saved.confirmed_agenda_ids

    async def test_counterpart_can_confirm_agenda(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        agenda_id = AgendaId.generate()
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id,
                agenda_id=agenda_id,
                actor_id=counterpart,
            )
        )

        assert isinstance(output, ConfirmAgendaOutput)
        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert agenda_id in saved.confirmed_agenda_ids

    async def test_multiple_agendas_can_be_confirmed(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        agenda1 = AgendaId.generate()
        agenda2 = AgendaId.generate()
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id, agenda_id=agenda1, actor_id=organizer
            )
        )
        await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id, agenda_id=agenda2, actor_id=organizer
            )
        )

        saved = await rr.get_by_id(record.id)
        assert saved is not None
        assert agenda1 in saved.confirmed_agenda_ids
        assert agenda2 in saved.confirmed_agenda_ids

    async def test_commits_transaction(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id,
                agenda_id=AgendaId.generate(),
                actor_id=organizer,
            )
        )

        assert uow.committed is True

    async def test_dispatches_agenda_confirmed_event(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        agenda_id = AgendaId.generate()
        uc, rr, _uow, ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id,
                agenda_id=agenda_id,
                actor_id=organizer,
            )
        )

        confirmed_events = [
            e for e in ed.dispatched_events if isinstance(e, AgendaConfirmed)
        ]
        assert len(confirmed_events) == 1
        event = confirmed_events[0]
        assert event.record_id == record.id
        assert event.agenda_id == agenda_id
        assert event.confirmed_by == organizer


class TestConfirmAgendaErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                ConfirmAgendaInput(
                    record_id=RecordId.generate(),
                    agenda_id=AgendaId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_viewer_tries_to_confirm(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(
            UnauthorizedOperationError, match="organizer or counterpart"
        ):
            await uc.execute(
                ConfirmAgendaInput(
                    record_id=record.id,
                    agenda_id=AgendaId.generate(),
                    actor_id=viewer,
                )
            )

    async def test_raises_when_agenda_already_confirmed(self) -> None:
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        agenda_id = AgendaId.generate()
        uc, rr, _uow, _ed = _build_use_case()
        await rr.save(record)
        record.collect_events()

        await uc.execute(
            ConfirmAgendaInput(
                record_id=record.id,
                agenda_id=agenda_id,
                actor_id=organizer,
            )
        )

        with pytest.raises(AgendaAlreadyConfirmedError):
            await uc.execute(
                ConfirmAgendaInput(
                    record_id=record.id,
                    agenda_id=agenda_id,
                    actor_id=organizer,
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
                ConfirmAgendaInput(
                    record_id=record.id,
                    agenda_id=AgendaId.generate(),
                    actor_id=organizer,
                )
            )

    async def test_does_not_commit_on_error(self) -> None:
        uc, _rr, uow, _ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                ConfirmAgendaInput(
                    record_id=RecordId.generate(),
                    agenda_id=AgendaId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        uc, _rr, _uow, ed = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                ConfirmAgendaInput(
                    record_id=RecordId.generate(),
                    agenda_id=AgendaId.generate(),
                    actor_id=UserId.generate(),
                )
            )

        assert ed.dispatched_events == []
