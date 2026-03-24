"""Tests for SaveTemplateService."""

from __future__ import annotations

import pytest

from contexts.preparation.application.save_template_service import (
    SaveTemplateInput,
    SaveTemplateOutput,
    SaveTemplateService,
)
from contexts.preparation.domain.events import TemplateSaved
from contexts.preparation.domain.exceptions import InvalidTemplateNameError
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryTemplateRepository,
    StubUnitOfWork,
)


class TestSaveTemplate:
    """Template saving use case."""

    @pytest.fixture
    def service(
        self,
        uow: StubUnitOfWork,
        template_repo: InMemoryTemplateRepository,
        dispatcher: InMemoryEventDispatcher,
    ) -> SaveTemplateService:
        return SaveTemplateService(
            uow=uow,
            template_repo=template_repo,
            event_dispatcher=dispatcher,
        )

    async def test_saves_template_with_all_fields(
        self,
        service: SaveTemplateService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Creates a template with name, counterparts, and agenda topics."""
        organizer = UserId.generate()
        cp1 = UserId.generate()
        cp2 = UserId.generate()

        output = await service.execute(
            SaveTemplateInput(
                organizer_id=organizer,
                name="Weekly 1on1 Template",
                default_counterpart_ids=[cp1, cp2],
                agenda_topics=["Progress update", "Blockers"],
            )
        )

        assert isinstance(output, SaveTemplateOutput)
        template = await template_repo.get_by_id(output.template_id)
        assert template is not None
        assert template.name.value == "Weekly 1on1 Template"
        assert template.organizer_id == organizer
        assert template.default_counterparts == [cp1, cp2]
        assert len(template.agenda_templates) == 2
        topics = [at.topic.value for at in template.agenda_templates]
        assert topics == ["Progress update", "Blockers"]

    async def test_saves_template_without_optional_fields(
        self,
        service: SaveTemplateService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Creates a template with empty counterparts and agenda topics."""
        organizer = UserId.generate()

        output = await service.execute(
            SaveTemplateInput(
                organizer_id=organizer,
                name="Minimal Template",
                default_counterpart_ids=[],
                agenda_topics=[],
            )
        )

        template = await template_repo.get_by_id(output.template_id)
        assert template is not None
        assert template.default_counterparts == []
        assert template.agenda_templates == []

    async def test_commits_via_uow(
        self,
        service: SaveTemplateService,
        uow: StubUnitOfWork,
    ) -> None:
        """Verifies that the service commits the transaction."""
        await service.execute(
            SaveTemplateInput(
                organizer_id=UserId.generate(),
                name="Test",
                default_counterpart_ids=[],
                agenda_topics=[],
            )
        )
        assert uow.committed is True

    async def test_dispatches_template_saved_event(
        self,
        uow: StubUnitOfWork,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Dispatches TemplateSaved event after commit."""
        dispatched: list[object] = []

        async def capture(event: object) -> None:
            dispatched.append(event)

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(TemplateSaved, capture)  # type: ignore[arg-type]

        svc = SaveTemplateService(
            uow=uow,
            template_repo=template_repo,
            event_dispatcher=dispatcher,
        )

        organizer = UserId.generate()
        await svc.execute(
            SaveTemplateInput(
                organizer_id=organizer,
                name="Event Test",
                default_counterpart_ids=[],
                agenda_topics=[],
            )
        )

        assert len(dispatched) == 1
        event = dispatched[0]
        assert isinstance(event, TemplateSaved)
        assert event.name == "Event Test"
        assert event.organizer_id == organizer

    async def test_rejects_invalid_template_name(
        self,
        service: SaveTemplateService,
    ) -> None:
        """Raises InvalidTemplateNameError for empty name."""
        with pytest.raises(InvalidTemplateNameError):
            await service.execute(
                SaveTemplateInput(
                    organizer_id=UserId.generate(),
                    name="   ",
                    default_counterpart_ids=[],
                    agenda_topics=[],
                )
            )
