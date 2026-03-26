"""Tests for GetTemplateQueryService."""

from __future__ import annotations

import pytest

from contexts.preparation.application.get_template_query_service import (
    GetTemplateInput,
    GetTemplateOutput,
    GetTemplateQueryService,
    TemplateNotFoundError,
    UnauthorizedTemplateAccessError,
)
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from contexts.preparation.domain.value_objects import TemplateId
from shared.domain.value_objects import UserId
from tests.contexts.preparation.application.conftest import (
    InMemoryTemplateRepository,
)


class TestGetTemplate:
    """Template retrieval use case."""

    @pytest.fixture
    def service(
        self,
        template_repo: InMemoryTemplateRepository,
    ) -> GetTemplateQueryService:
        return GetTemplateQueryService(template_repo=template_repo)

    async def test_returns_template_for_owner(
        self,
        service: GetTemplateQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Returns template details when requested by the owner."""
        organizer = UserId.generate()
        cp = UserId.generate()

        t = Template.create(
            organizer_id=organizer,
            name=TemplateName("My Template"),
            default_counterparts=[cp],
            agenda_templates=[AgendaTemplate("Topic A")],
        )
        # Drain events from create to avoid side effects in assertion
        t.collect_events()
        await template_repo.save(t)

        output = await service.execute(
            GetTemplateInput(template_id=t.id, actor_id=organizer)
        )

        assert isinstance(output, GetTemplateOutput)
        assert output.template_id == t.id
        assert output.organizer_id == organizer
        assert output.name == "My Template"
        assert output.default_counterpart_ids == [cp]
        assert output.agenda_topics == ["Topic A"]

    async def test_raises_not_found_for_missing_template(
        self,
        service: GetTemplateQueryService,
    ) -> None:
        """Raises TemplateNotFoundError for non-existent template."""
        with pytest.raises(TemplateNotFoundError):
            await service.execute(
                GetTemplateInput(
                    template_id=TemplateId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_unauthorized_for_non_owner(
        self,
        service: GetTemplateQueryService,
        template_repo: InMemoryTemplateRepository,
    ) -> None:
        """Raises UnauthorizedTemplateAccessError for non-owner."""
        organizer = UserId.generate()
        other_user = UserId.generate()

        t = Template.create(
            organizer_id=organizer,
            name=TemplateName("Private Template"),
        )
        t.collect_events()
        await template_repo.save(t)

        with pytest.raises(UnauthorizedTemplateAccessError):
            await service.execute(
                GetTemplateInput(template_id=t.id, actor_id=other_user)
            )
