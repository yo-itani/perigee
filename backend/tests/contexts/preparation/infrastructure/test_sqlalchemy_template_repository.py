from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.template import Template
from contexts.preparation.domain.template_name import TemplateName
from contexts.preparation.domain.value_objects import TemplateId
from contexts.preparation.infrastructure.sqlalchemy_template_repository import (
    SqlAlchemyTemplateRepository,
)
from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable

pytestmark = pytest.mark.integration

NOW = datetime(2026, 4, 1, 10, 0)


async def _create_user(session: AsyncSession) -> UserId:
    user_id = UserId.generate()
    session.add(UserTable(id=str(user_id.value)))
    await session.flush()
    return user_id


def _make_template(
    *,
    organizer_id: UserId,
    name: str = "Default Template",
    default_counterparts: list[UserId] | None = None,
    agenda_templates: list[AgendaTemplate] | None = None,
    now: datetime = NOW,
) -> Template:
    return Template.create(
        organizer_id=organizer_id,
        name=TemplateName(name),
        default_counterparts=default_counterparts,
        agenda_templates=agenda_templates,
        now=now,
    )


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_minimal_template(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)

        template = _make_template(organizer_id=org)
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        assert loaded.id == template.id
        assert loaded.organizer_id == org
        assert loaded.name == TemplateName("Default Template")
        assert loaded.default_counterparts == []
        assert loaded.agenda_templates == []

    async def test_save_with_counterparts_and_agendas(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)
        cp1 = await _create_user(session)
        cp2 = await _create_user(session)

        template = _make_template(
            organizer_id=org,
            default_counterparts=[cp1, cp2],
            agenda_templates=[AgendaTemplate("Topic A"), AgendaTemplate("Topic B")],
        )
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        assert len(loaded.default_counterparts) == 2
        assert loaded.default_counterparts[0] == cp1
        assert loaded.default_counterparts[1] == cp2
        assert len(loaded.agenda_templates) == 2
        assert loaded.agenda_templates[0].topic.value == "Topic A"
        assert loaded.agenda_templates[1].topic.value == "Topic B"

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        result = await repo.get_by_id(TemplateId.generate())
        assert result is None


class TestUpdateTemplate:
    """save() with template updates."""

    async def test_update_name_and_lists(self, session: AsyncSession) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)
        cp1 = await _create_user(session)
        cp2 = await _create_user(session)

        template = _make_template(
            organizer_id=org,
            default_counterparts=[cp1],
            agenda_templates=[AgendaTemplate("Old Topic")],
        )
        await repo.save(template)
        await session.commit()

        # Update via domain method
        template.update(
            actor_id=org,
            name=TemplateName("Updated Template"),
            default_counterparts=[cp2, cp1],
            agenda_templates=[
                AgendaTemplate("New Topic A"),
                AgendaTemplate("New Topic B"),
            ],
            now=datetime(2026, 4, 2, 10, 0),
        )
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        assert loaded.name == TemplateName("Updated Template")
        assert len(loaded.default_counterparts) == 2
        assert loaded.default_counterparts[0] == cp2
        assert loaded.default_counterparts[1] == cp1
        assert len(loaded.agenda_templates) == 2
        assert loaded.agenda_templates[0].topic.value == "New Topic A"
        assert loaded.agenda_templates[1].topic.value == "New Topic B"

    async def test_update_removes_all_children(self, session: AsyncSession) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)
        cp1 = await _create_user(session)

        template = _make_template(
            organizer_id=org,
            default_counterparts=[cp1],
            agenda_templates=[AgendaTemplate("Topic")],
        )
        await repo.save(template)
        await session.commit()

        # Update to empty lists
        template.update(
            actor_id=org,
            name=TemplateName("Empty Template"),
            default_counterparts=[],
            agenda_templates=[],
            now=datetime(2026, 4, 2, 10, 0),
        )
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        assert loaded.default_counterparts == []
        assert loaded.agenda_templates == []


class TestPositionOrdering:
    """Verify position-based ordering is preserved."""

    async def test_counterpart_order_preserved(self, session: AsyncSession) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)
        users = [await _create_user(session) for _ in range(5)]

        template = _make_template(
            organizer_id=org,
            default_counterparts=users,
        )
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        assert loaded.default_counterparts == users

    async def test_agenda_template_order_preserved(self, session: AsyncSession) -> None:
        repo = SqlAlchemyTemplateRepository(session)
        org = await _create_user(session)

        topics = [f"Topic {i}" for i in range(5)]
        agenda_templates = [AgendaTemplate(t) for t in topics]

        template = _make_template(
            organizer_id=org,
            agenda_templates=agenda_templates,
        )
        await repo.save(template)
        await session.commit()

        loaded = await repo.get_by_id(template.id)

        assert loaded is not None
        loaded_topics = [at.topic.value for at in loaded.agenda_templates]
        assert loaded_topics == topics
