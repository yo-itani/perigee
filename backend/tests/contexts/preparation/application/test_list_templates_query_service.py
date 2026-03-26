"""Tests for ListTemplatesQueryService."""

from __future__ import annotations

import pytest

from contexts.preparation.application.list_templates_query_service import (
    ListTemplatesInput,
    ListTemplatesQueryService,
)
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryTemplateRepository,
)


class TestListTemplates:
    """Template listing use case."""

    @pytest.fixture
    def service(
        self,
        template_repo: InMemoryTemplateRepository,
    ) -> ListTemplatesQueryService:
        return ListTemplatesQueryService(template_repo=template_repo)

    async def test_returns_templates_for_organizer(
        self,
        service: ListTemplatesQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Returns all templates owned by the given organizer."""
        organizer = UserId.generate()
        cp = UserId.generate()

        t1 = Template.create(
            organizer_id=organizer,
            name=TemplateName("Template A"),
            default_counterparts=[cp],
            agenda_templates=[AgendaTemplate("Topic 1")],
        )
        t2 = Template.create(
            organizer_id=organizer,
            name=TemplateName("Template B"),
        )
        await template_repo.save(t1)
        await template_repo.save(t2)

        output = await service.execute(ListTemplatesInput(actor_id=organizer))

        assert len(output.templates) == 2
        names = {t.name for t in output.templates}
        assert names == {"Template A", "Template B"}

    async def test_does_not_return_other_organizers_templates(
        self,
        service: ListTemplatesQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Does not return templates owned by a different organizer."""
        organizer1 = UserId.generate()
        organizer2 = UserId.generate()

        t1 = Template.create(
            organizer_id=organizer1,
            name=TemplateName("Org1 Template"),
        )
        t2 = Template.create(
            organizer_id=organizer2,
            name=TemplateName("Org2 Template"),
        )
        await template_repo.save(t1)
        await template_repo.save(t2)

        output = await service.execute(ListTemplatesInput(actor_id=organizer1))

        assert len(output.templates) == 1
        assert output.templates[0].name == "Org1 Template"

    async def test_returns_empty_list_when_no_templates(
        self,
        service: ListTemplatesQueryService,
    ) -> None:
        """Returns an empty list when the organizer has no templates."""
        output = await service.execute(ListTemplatesInput(actor_id=UserId.generate()))
        assert output.templates == []

    async def test_includes_template_details(
        self,
        service: ListTemplatesQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Each list item includes counterparts and agenda topics."""
        organizer = UserId.generate()
        cp = UserId.generate()

        t = Template.create(
            organizer_id=organizer,
            name=TemplateName("Detailed"),
            default_counterparts=[cp],
            agenda_templates=[AgendaTemplate("Topic A"), AgendaTemplate("Topic B")],
        )
        await template_repo.save(t)

        output = await service.execute(ListTemplatesInput(actor_id=organizer))

        item = output.templates[0]
        assert item.name == "Detailed"
        assert item.default_counterpart_ids == [cp]
        assert item.agenda_topics == ["Topic A", "Topic B"]
        assert item.template_id == t.id
        assert item.created_at == t.created_at
        assert item.updated_at == t.updated_at

    async def test_actor_cannot_list_other_users_templates(
        self,
        service: ListTemplatesQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """An actor cannot retrieve templates owned by another user."""
        owner = UserId.generate()
        other = UserId.generate()

        t = Template.create(
            organizer_id=owner,
            name=TemplateName("Owner Template"),
        )
        await template_repo.save(t)

        output = await service.execute(ListTemplatesInput(actor_id=other))

        assert output.templates == []
