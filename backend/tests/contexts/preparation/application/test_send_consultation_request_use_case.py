"""Tests for SendConsultationRequestUseCase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.send_consultation_request_use_case import (
    SendConsultationRequestInput,
    SendConsultationRequestOutput,
    SendConsultationRequestUseCase,
)
from contexts.preparation.domain.events import ScheduleCreated
from contexts.preparation.domain.exceptions import (
    InvalidScheduleOperationError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.value_objects import (
    ConfirmationRequestType,
    ConfirmationResolution,
    ScheduleStatus,
)
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
    InMemoryScheduleRepository,
    StubUnitOfWork,
)


class TestSendConsultationRequest:
    """Send a consultation request (ad-hoc pattern B)."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> SendConsultationRequestUseCase:
        return SendConsultationRequestUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    async def test_creates_requested_schedule(
        self,
        service: SendConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Schedule is created in REQUESTED status with counterpart as requester."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=["Topic A"],
                actor_id=counterpart,
            )
        )

        assert isinstance(output, SendConsultationRequestOutput)
        schedule = await schedule_repo.get_by_id(output.schedule_id)
        assert schedule is not None
        assert schedule.status == ScheduleStatus.REQUESTED
        assert schedule.organizer_id == organizer
        assert schedule.counterpart_id == counterpart

    async def test_creates_creation_type_confirmation_request(
        self,
        service: SendConsultationRequestUseCase,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """A CREATION-type ConfirmationRequest is generated as pending."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=[],
                actor_id=counterpart,
            )
        )

        schedule = await schedule_repo.get_by_id(output.schedule_id)
        assert schedule is not None
        requests = schedule.confirmation_requests
        assert len(requests) == 1
        assert requests[0].request_type == ConfirmationRequestType.CREATION
        assert requests[0].resolution == ConfirmationResolution.PENDING
        assert requests[0].requested_by == counterpart

    async def test_creates_agendas(
        self,
        service: SendConsultationRequestUseCase,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Counterpart's agenda topics are persisted."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=["Career discussion", "Project update"],
                actor_id=counterpart,
            )
        )

        agendas = await agenda_repo.get_by_schedule_id(output.schedule_id)
        assert len(agendas) == 2
        topics = {a.topic.value for a in agendas}
        assert topics == {"Career discussion", "Project update"}
        for agenda in agendas:
            assert agenda.added_by == counterpart

    async def test_dispatches_schedule_created_event(
        self,
        uow: StubUnitOfWork,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """ScheduleCreated event is dispatched after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCreated, capture)  # type: ignore[arg-type]

        service = SendConsultationRequestUseCase(
            uow=uow,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=[],
                actor_id=counterpart,
            )
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, ScheduleCreated)
        assert event.requested_by == counterpart

    async def test_organizer_cannot_send_consultation_request(
        self,
        service: SendConsultationRequestUseCase,
    ) -> None:
        """Organizer attempting to send raises UnauthorizedScheduleOperationError."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(UnauthorizedScheduleOperationError):
            await service.execute(
                SendConsultationRequestInput(
                    organizer_id=organizer,
                    counterpart_id=counterpart,
                    scheduled_at=scheduled_at,
                    title="Ad-hoc consultation",
                    agenda_topics=[],
                    actor_id=organizer,
                )
            )

    async def test_third_party_cannot_send_consultation_request(
        self,
        service: SendConsultationRequestUseCase,
    ) -> None:
        """A third-party user cannot send a consultation request."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        outsider = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(UnauthorizedScheduleOperationError):
            await service.execute(
                SendConsultationRequestInput(
                    organizer_id=organizer,
                    counterpart_id=counterpart,
                    scheduled_at=scheduled_at,
                    title="Ad-hoc consultation",
                    agenda_topics=[],
                    actor_id=outsider,
                )
            )

    async def test_rejects_past_datetime(
        self,
        service: SendConsultationRequestUseCase,
    ) -> None:
        """Raises InvalidScheduleOperationError for past scheduled_at."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        past_time = datetime.now(UTC) - timedelta(days=1)

        with pytest.raises(InvalidScheduleOperationError):
            await service.execute(
                SendConsultationRequestInput(
                    organizer_id=organizer,
                    counterpart_id=counterpart,
                    scheduled_at=past_time,
                    title="Ad-hoc consultation",
                    agenda_topics=[],
                    actor_id=counterpart,
                )
            )

    async def test_commits_via_uow(
        self,
        service: SendConsultationRequestUseCase,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=[],
                actor_id=counterpart,
            )
        )
        assert uow.committed is True

    async def test_no_agendas_is_valid(
        self,
        service: SendConsultationRequestUseCase,
        agenda_repo: InMemoryAgendaRepository,
    ) -> None:
        """Empty agenda_topics list is allowed (counterpart may add later)."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        scheduled_at = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            SendConsultationRequestInput(
                organizer_id=organizer,
                counterpart_id=counterpart,
                scheduled_at=scheduled_at,
                title="Ad-hoc consultation",
                agenda_topics=[],
                actor_id=counterpart,
            )
        )

        agendas = await agenda_repo.get_by_schedule_id(output.schedule_id)
        assert len(agendas) == 0
