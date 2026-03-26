"""Tests for AcceptConsultationRequestUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.accept_consultation_request_use_case import (
    AcceptConsultationRequestInput,
    AcceptConsultationRequestUseCase,
    ScheduleNotFoundError,
)
from contexts.preparation.domain.events import ScheduleConfirmed
from contexts.preparation.domain.exceptions import (
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId, ScheduleStatus
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


def _create_consultation_schedule(
    organizer: UserId,
    counterpart: UserId,
    scheduled_at: datetime | None = None,
) -> Schedule:
    """Helper to create a schedule in REQUESTED status via counterpart request."""
    ts = scheduled_at or datetime.now(UTC) + timedelta(days=1)
    schedule = Schedule.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        scheduled_at=ts,
        requested_by=counterpart,
        title=ScheduleTitle("Consultation"),
    )
    schedule.collect_events()  # Clear creation events
    return schedule


class TestAcceptConsultationRequest:
    """Accept a consultation request (ad-hoc pattern B)."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> AcceptConsultationRequestUseCase:
        return AcceptConsultationRequestUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

    async def test_confirms_schedule(
        self,
        service: AcceptConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Schedule transitions from REQUESTED to CONFIRMED."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        await schedule_repo.save(schedule)

        await service.execute(
            AcceptConsultationRequestInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )

        updated = await schedule_repo.get_by_id(schedule.id)
        assert updated is not None
        assert updated.status == ScheduleStatus.CONFIRMED

    async def test_dispatches_confirmed_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """ScheduleConfirmed event is dispatched after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleConfirmed, capture)  # type: ignore[arg-type]

        service = AcceptConsultationRequestUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        await schedule_repo.save(schedule)

        await service.execute(
            AcceptConsultationRequestInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, ScheduleConfirmed)
        assert event.confirmed_by == organizer
        assert event.is_auto is False

    async def test_counterpart_cannot_accept(
        self,
        service: AcceptConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Counterpart cannot accept a consultation request."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedScheduleOperationError):
            await service.execute(
                AcceptConsultationRequestInput(
                    schedule_id=schedule.id,
                    actor_id=counterpart,
                )
            )

    async def test_third_party_cannot_accept(
        self,
        service: AcceptConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """A third-party user cannot accept a consultation request."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        await schedule_repo.save(schedule)

        with pytest.raises(UnauthorizedScheduleOperationError):
            await service.execute(
                AcceptConsultationRequestInput(
                    schedule_id=schedule.id,
                    actor_id=outsider,
                )
            )

    async def test_schedule_not_found(
        self,
        service: AcceptConsultationRequestUseCase,
    ) -> None:
        """Raises ScheduleNotFoundError for non-existent schedule."""
        with pytest.raises(ScheduleNotFoundError):
            await service.execute(
                AcceptConsultationRequestInput(
                    schedule_id=ScheduleId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_cancelled_schedule_cannot_be_accepted(
        self,
        service: AcceptConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Raises ScheduleAlreadyCancelledError for cancelled schedule."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        schedule.cancel(actor_id=organizer, now=datetime.now(UTC))
        schedule.collect_events()
        await schedule_repo.save(schedule)

        with pytest.raises(ScheduleAlreadyCancelledError):
            await service.execute(
                AcceptConsultationRequestInput(
                    schedule_id=schedule.id,
                    actor_id=organizer,
                )
            )

    async def test_commits_via_uow(
        self,
        service: AcceptConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _create_consultation_schedule(organizer, counterpart)
        await schedule_repo.save(schedule)

        await service.execute(
            AcceptConsultationRequestInput(
                schedule_id=schedule.id,
                actor_id=organizer,
            )
        )
        assert uow.committed is True
