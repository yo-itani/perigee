"""Tests for SuggestDefaultViewersUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.record.application.suggest_default_viewers import (
    RecordNotFoundError,
    SuggestDefaultViewersInput,
    SuggestDefaultViewersOutput,
    SuggestDefaultViewersUseCase,
)
from contexts.record.domain.captain_query_service import CaptainQueryService
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from shared.domain.value_objects import UserId
from tests.contexts.record.application.conftest import InMemoryRecordRepository


class StubCaptainQueryService(CaptainQueryService):
    """Stub that returns a preconfigured list of captain IDs."""

    def __init__(self, captain_ids: list[UserId] | None = None) -> None:
        self._captain_ids = captain_ids or []

    async def get_captains_for_user(self, user_id: UserId) -> list[UserId]:
        return list(self._captain_ids)


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
    captain_query_service: StubCaptainQueryService | None = None,
) -> tuple[
    SuggestDefaultViewersUseCase,
    InMemoryRecordRepository,
    StubCaptainQueryService,
]:
    rr = record_repo or InMemoryRecordRepository()
    cqs = captain_query_service or StubCaptainQueryService()
    uc = SuggestDefaultViewersUseCase(
        record_repository=rr,
        captain_query_service=cqs,
    )
    return uc, rr, cqs


class TestSuggestDefaultViewers:
    """Tests for successful default viewer suggestion."""

    async def test_returns_captain_suggestions(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        captain = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)

        uc, rr, _cqs = _build_use_case(
            captain_query_service=StubCaptainQueryService([captain])
        )
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SuggestDefaultViewersInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert isinstance(output, SuggestDefaultViewersOutput)
        assert captain in output.suggested_viewer_ids

    async def test_excludes_organizer_from_suggestions(self) -> None:
        """If the organizer is also a Captain for the counterpart, exclude them."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        other_captain = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)

        uc, rr, _cqs = _build_use_case(
            captain_query_service=StubCaptainQueryService([organizer, other_captain])
        )
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SuggestDefaultViewersInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert organizer not in output.suggested_viewer_ids
        assert other_captain in output.suggested_viewer_ids

    async def test_excludes_counterpart_from_suggestions(self) -> None:
        """Counterpart is implicit; should not appear in suggestions."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        captain = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)

        uc, rr, _cqs = _build_use_case(
            captain_query_service=StubCaptainQueryService([counterpart, captain])
        )
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SuggestDefaultViewersInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert counterpart not in output.suggested_viewer_ids
        assert captain in output.suggested_viewer_ids

    async def test_returns_empty_when_no_captains(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)

        uc, rr, _cqs = _build_use_case(
            captain_query_service=StubCaptainQueryService([])
        )
        await rr.save(record)
        record.collect_events()

        output = await uc.execute(
            SuggestDefaultViewersInput(
                record_id=record.id,
                actor_id=organizer,
            )
        )

        assert output.suggested_viewer_ids == []


class TestSuggestDefaultViewersErrors:
    """Tests for error conditions."""

    async def test_raises_when_record_not_found(self) -> None:
        uc, _rr, _cqs = _build_use_case()

        with pytest.raises(RecordNotFoundError):
            await uc.execute(
                SuggestDefaultViewersInput(
                    record_id=RecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_is_not_organizer(self) -> None:
        """Non-organizer cannot suggest default viewers."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        record = _make_draft_record(organizer=organizer, counterpart=counterpart)
        uc, rr, _cqs = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                SuggestDefaultViewersInput(
                    record_id=record.id,
                    actor_id=counterpart,
                )
            )

    async def test_raises_when_actor_is_unrelated(self) -> None:
        """Unrelated user cannot suggest default viewers."""
        organizer = UserId.generate()
        record = _make_draft_record(organizer=organizer)
        uc, rr, _cqs = _build_use_case()
        await rr.save(record)
        record.collect_events()

        with pytest.raises(UnauthorizedOperationError, match="Only the organizer"):
            await uc.execute(
                SuggestDefaultViewersInput(
                    record_id=record.id,
                    actor_id=UserId.generate(),
                )
            )
