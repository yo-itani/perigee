from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleGroupId
from contexts.preparation.infrastructure.sqlalchemy_schedule_group_repository import (
    SqlAlchemyScheduleGroupRepository,
)
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    SqlAlchemyScheduleRepository,
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


def _make_schedule_group(
    *,
    organizer_id: UserId,
    title: str = "Weekly Group",
    agenda_templates: list[AgendaTemplate] | None = None,
    now: datetime = NOW,
) -> ScheduleGroup:
    return ScheduleGroup.create(
        organizer_id=organizer_id,
        title=ScheduleTitle(title),
        agenda_templates=agenda_templates,
        now=now,
    )


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_empty_group(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleGroupRepository(session)
        org = await _create_user(session)

        group = _make_schedule_group(organizer_id=org)
        await repo.save(group)
        await session.commit()

        loaded = await repo.get_by_id(group.id)

        assert loaded is not None
        assert loaded.id == group.id
        assert loaded.organizer_id == org
        assert loaded.title == ScheduleTitle("Weekly Group")
        assert loaded.template_id is None
        assert loaded.agenda_templates == []
        assert loaded.schedule_ids == []

    async def test_save_with_agenda_templates(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleGroupRepository(session)
        org = await _create_user(session)

        templates = [AgendaTemplate("Progress"), AgendaTemplate("Blockers")]
        group = _make_schedule_group(organizer_id=org, agenda_templates=templates)
        await repo.save(group)
        await session.commit()

        loaded = await repo.get_by_id(group.id)

        assert loaded is not None
        assert len(loaded.agenda_templates) == 2
        assert loaded.agenda_templates[0].topic.value == "Progress"
        assert loaded.agenda_templates[1].topic.value == "Blockers"

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyScheduleGroupRepository(session)
        result = await repo.get_by_id(ScheduleGroupId.generate())
        assert result is None


class TestScheduleIdsRestoration:
    """schedule_ids are restored from the schedules table."""

    async def test_schedule_ids_restored_in_order(self, session: AsyncSession) -> None:
        group_repo = SqlAlchemyScheduleGroupRepository(session)
        schedule_repo = SqlAlchemyScheduleRepository(session)
        org = await _create_user(session)
        cp = await _create_user(session)

        group = _make_schedule_group(organizer_id=org)
        await group_repo.save(group)

        # Create schedules belonging to this group
        s1 = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=datetime(2026, 4, 10, 14, 0),
            requested_by=org,
            title=ScheduleTitle("Meeting 1"),
            schedule_group_id=group.id,
            now=datetime(2026, 4, 1, 10, 0, 0),
        )
        s2 = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=datetime(2026, 4, 17, 14, 0),
            requested_by=org,
            title=ScheduleTitle("Meeting 2"),
            schedule_group_id=group.id,
            now=datetime(2026, 4, 1, 10, 0, 1),
        )
        await schedule_repo.save(s1)
        await schedule_repo.save(s2)
        await session.commit()

        loaded = await group_repo.get_by_id(group.id)

        assert loaded is not None
        assert len(loaded.schedule_ids) == 2
        assert loaded.schedule_ids[0] == s1.id
        assert loaded.schedule_ids[1] == s2.id


class TestUpdateAgendaTemplates:
    """save() with agenda template changes."""

    async def test_add_agenda_template(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleGroupRepository(session)
        org = await _create_user(session)

        group = _make_schedule_group(
            organizer_id=org,
            agenda_templates=[AgendaTemplate("Topic A")],
        )
        await repo.save(group)
        await session.commit()

        # Modify agenda templates via internal state for testing persistence
        group._agenda_templates.append(AgendaTemplate("Topic B"))
        group._updated_at = datetime(2026, 4, 2, 10, 0)
        await repo.save(group)
        await session.commit()

        loaded = await repo.get_by_id(group.id)
        assert loaded is not None
        assert len(loaded.agenda_templates) == 2
        assert loaded.agenda_templates[0].topic.value == "Topic A"
        assert loaded.agenda_templates[1].topic.value == "Topic B"

    async def test_remove_agenda_template(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleGroupRepository(session)
        org = await _create_user(session)

        group = _make_schedule_group(
            organizer_id=org,
            agenda_templates=[AgendaTemplate("Keep"), AgendaTemplate("Remove")],
        )
        await repo.save(group)
        await session.commit()

        # Remove second template
        group._agenda_templates.pop(1)
        group._updated_at = datetime(2026, 4, 2, 10, 0)
        await repo.save(group)
        await session.commit()

        loaded = await repo.get_by_id(group.id)
        assert loaded is not None
        assert len(loaded.agenda_templates) == 1
        assert loaded.agenda_templates[0].topic.value == "Keep"
