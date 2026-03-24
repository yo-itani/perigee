"""Tests for CreateScheduleGroupFromTemplateService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    CreateScheduleGroupFromTemplateInput,
    CreateScheduleGroupFromTemplateOutput,
    CreateScheduleGroupFromTemplateService,
    TemplateCounterpartSchedule,
    TemplateNotFoundError,
    UnauthorizedTemplateUseError,
)
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import ScheduleCreated, ScheduleGroupCreated
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from contexts.preparation.domain.value_objects import ScheduleStatus, TemplateId
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryAgendaRepository,
    InMemoryScheduleGroupRepository,
    InMemoryScheduleRepository,
    InMemoryTemplateRepository,
    StubUnitOfWork,
)


class TestCreateScheduleGroupFromTemplate:
    """ScheduleGroup creation from a saved template."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        template_repo: InMemoryTemplateRepository,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> CreateScheduleGroupFromTemplateService:
        return CreateScheduleGroupFromTemplateService(
            uow=uow,
            template_repo=template_repo,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

    @pytest.fixture
    def organizer(self) -> UserId:
        return UserId.generate()

    @pytest.fixture
    async def template_with_agendas(
        self,
        organizer: UserId,
        template_repo: InMemoryTemplateRepository,
    ) -> Template:
        """A template with 2 agenda topics and 1 default counterpart."""
        cp = UserId.generate()
        t = Template.create(
            organizer_id=organizer,
            name=TemplateName("Weekly Template"),
            default_counterparts=[cp],
            agenda_templates=[AgendaTemplate("Progress"), AgendaTemplate("Blockers")],
        )
        t.collect_events()
        await template_repo.save(t)
        return t

    async def test_creates_group_from_template(
        self,
        service: CreateScheduleGroupFromTemplateService,
        template_with_agendas: Template,
        organizer: UserId,
        schedule_group_repo: InMemoryScheduleGroupRepository,
    ) -> None:
        """Creates a ScheduleGroup referencing the template."""
        cp1 = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        output = await service.execute(
            CreateScheduleGroupFromTemplateInput(
                organizer_id=organizer,
                template_id=template_with_agendas.id,
                title="From Template",
                counterpart_schedules=[
                    TemplateCounterpartSchedule(
                        counterpart_id=cp1, scheduled_at=future
                    ),
                ],
            )
        )

        assert isinstance(output, CreateScheduleGroupFromTemplateOutput)
        group = await schedule_group_repo.get_by_id(output.schedule_group_id)
        assert group is not None
        assert group.title.value == "From Template"
        assert group.template_id == template_with_agendas.id
        assert len(group.schedule_ids) == 1

    async def test_expands_template_agendas(
        self,
        service: CreateScheduleGroupFromTemplateService,
        template_with_agendas: Template,
        organizer: UserId,
        agenda_repo: InMemoryAgendaRepository,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Template agenda topics are expanded into Agenda entities."""
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        await service.execute(
            CreateScheduleGroupFromTemplateInput(
                organizer_id=organizer,
                template_id=template_with_agendas.id,
                title="With Agendas",
                counterpart_schedules=[
                    TemplateCounterpartSchedule(
                        counterpart_id=cp1, scheduled_at=future
                    ),
                    TemplateCounterpartSchedule(
                        counterpart_id=cp2,
                        scheduled_at=future + timedelta(hours=1),
                    ),
                ],
            )
        )

        # 2 counterparts * 2 topics = 4 agendas
        assert len(agenda_repo.agendas) == 4

        for schedule in schedule_repo.schedules.values():
            schedule_agendas = await agenda_repo.get_by_schedule_id(schedule.id)
            assert len(schedule_agendas) == 2
            topics = {a.topic.value for a in schedule_agendas}
            assert topics == {"Progress", "Blockers"}

    async def test_raises_not_found_for_missing_template(
        self,
        service: CreateScheduleGroupFromTemplateService,
        organizer: UserId,
    ) -> None:
        """Raises TemplateNotFoundError when template does not exist."""
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(TemplateNotFoundError):
            await service.execute(
                CreateScheduleGroupFromTemplateInput(
                    organizer_id=organizer,
                    template_id=TemplateId.generate(),
                    title="Missing",
                    counterpart_schedules=[
                        TemplateCounterpartSchedule(
                            counterpart_id=UserId.generate(),
                            scheduled_at=future,
                        ),
                    ],
                )
            )

    async def test_raises_unauthorized_for_non_owner(
        self,
        service: CreateScheduleGroupFromTemplateService,
        template_with_agendas: Template,
    ) -> None:
        """Raises UnauthorizedTemplateUseError for non-owner."""
        other_user = UserId.generate()
        future = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(UnauthorizedTemplateUseError):
            await service.execute(
                CreateScheduleGroupFromTemplateInput(
                    organizer_id=other_user,
                    template_id=template_with_agendas.id,
                    title="Unauthorized",
                    counterpart_schedules=[
                        TemplateCounterpartSchedule(
                            counterpart_id=UserId.generate(),
                            scheduled_at=future,
                        ),
                    ],
                )
            )

    async def test_commits_via_uow(
        self,
        service: CreateScheduleGroupFromTemplateService,
        template_with_agendas: Template,
        organizer: UserId,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            CreateScheduleGroupFromTemplateInput(
                organizer_id=organizer,
                template_id=template_with_agendas.id,
                title="Commit Test",
                counterpart_schedules=[
                    TemplateCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )
        )
        assert uow.committed is True

    async def test_dispatches_events(
        self,
        uow: StubUnitOfWork,
        template_repo: InMemoryTemplateRepository,
        schedule_group_repo: InMemoryScheduleGroupRepository,
        schedule_repo: InMemoryScheduleRepository,
        agenda_repo: InMemoryAgendaRepository,
        template_with_agendas: Template,
        organizer: UserId,
    ) -> None:
        """Dispatches ScheduleCreated and ScheduleGroupCreated events."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(ScheduleCreated, capture)  # type: ignore[arg-type]
        dispatcher.register(ScheduleGroupCreated, capture)  # type: ignore[arg-type]

        svc = CreateScheduleGroupFromTemplateService(
            uow=uow,
            template_repo=template_repo,
            schedule_group_repo=schedule_group_repo,
            schedule_repo=schedule_repo,
            agenda_repo=agenda_repo,
            event_dispatcher=dispatcher,
        )

        future = datetime.now(UTC) + timedelta(days=1)
        await svc.execute(
            CreateScheduleGroupFromTemplateInput(
                organizer_id=organizer,
                template_id=template_with_agendas.id,
                title="Events Test",
                counterpart_schedules=[
                    TemplateCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )
        )

        schedule_created = [e for e in dispatched if isinstance(e, ScheduleCreated)]
        group_created = [e for e in dispatched if isinstance(e, ScheduleGroupCreated)]
        assert len(schedule_created) == 1
        assert len(group_created) == 1

    async def test_schedules_in_requested_status(
        self,
        service: CreateScheduleGroupFromTemplateService,
        template_with_agendas: Template,
        organizer: UserId,
        schedule_repo: InMemoryScheduleRepository,
    ) -> None:
        """Created schedules start in REQUESTED status."""
        future = datetime.now(UTC) + timedelta(days=1)
        await service.execute(
            CreateScheduleGroupFromTemplateInput(
                organizer_id=organizer,
                template_id=template_with_agendas.id,
                title="Status Test",
                counterpart_schedules=[
                    TemplateCounterpartSchedule(
                        counterpart_id=UserId.generate(), scheduled_at=future
                    ),
                ],
            )
        )

        for schedule in schedule_repo.schedules.values():
            assert schedule.status == ScheduleStatus.REQUESTED
