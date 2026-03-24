"""Tests for GetViewersUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.get_viewers import (
    GetViewersInput,
    GetViewersOutput,
    GetViewersUseCase,
    RecordNotFoundError,
)
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import InMemoryRecordRepository


def _make_record_with_viewers(
    organizer: UserId,
    counterpart: UserId,
    viewer_ids: list[UserId],
) -> Record:
    record = Record.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        conducted_at=datetime(2026, 3, 25, 10, 0),
    )
    record.set_viewers(
        viewer_ids=viewer_ids,
        actor_id=organizer,
        now=datetime(2026, 3, 25, 10, 5),
    )
    return record


def _build_use_case(
    record_repo: InMemoryRecordRepository | None = None,
) -> tuple[GetViewersUseCase, InMemoryRecordRepository]:
    rr = record_repo or InMemoryRecordRepository()
    uc = GetViewersUseCase(record_repository=rr)
    return uc, rr


class TestGetViewers:
    """Tests for successful viewer retrieval."""

    async def test_organizer_can_get_viewers(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_record_with_viewers(organizer, counterpart, [viewer])
        uc, rr = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            GetViewersInput(record_id=record.id, actor_id=organizer)
        )

        assert isinstance(output, GetViewersOutput)
        assert viewer in output.viewer_ids

    async def test_counterpart_can_get_viewers(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_record_with_viewers(organizer, counterpart, [viewer])
        uc, rr = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            GetViewersInput(record_id=record.id, actor_id=counterpart)
        )

        assert viewer in output.viewer_ids

    async def test_returns_empty_when_no_viewers(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record_with_viewers(organizer, counterpart, [])
        uc, rr = _build_use_case()
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            GetViewersInput(record_id=record.id, actor_id=organizer)
        )

        assert output.viewer_ids == []


class TestGetViewersErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                GetViewersInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_is_viewer(self) -> None:
        """Viewers cannot see the viewers list."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        viewer = UserId.generate()
        record = _make_record_with_viewers(organizer, counterpart, [viewer])
        uc, rr = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(GetViewersInput(record_id=record.id, actor_id=viewer))

    async def test_raises_when_actor_is_unrelated(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_record_with_viewers(organizer, counterpart, [])
        uc, rr = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                GetViewersInput(
                    record_id=record.id,
                    actor_id=UserId.generate(),
                )
            )
