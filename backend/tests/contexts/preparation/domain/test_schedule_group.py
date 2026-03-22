from datetime import datetime

import pytest

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import (
    AgendaAddedViaGroup,
    AgendaRemovedViaGroup,
    ScheduleGroupCreated,
)
from contexts.preparation.domain.exceptions import (
    InconsistentScheduleAgendasError,
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import ScheduleId, TemplateId
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_group(
    *,
    organizer_id: UserId | None = None,
    agenda_templates: list[AgendaTemplate] | None = None,
    template_id: TemplateId | None = None,
    now: datetime = _NOW,
) -> ScheduleGroup:
    return ScheduleGroup.create(
        organizer_id=organizer_id or UserId.generate(),
        agenda_templates=agenda_templates,
        template_id=template_id,
        now=now,
    )


def _make_group_with_schedules(
    *,
    organizer_id: UserId | None = None,
    schedule_count: int = 3,
    now: datetime = _NOW,
) -> tuple[ScheduleGroup, list[ScheduleId]]:
    """Create a group with registered schedules."""
    org = organizer_id or UserId.generate()
    group = _make_group(organizer_id=org, now=now)
    schedule_ids = [ScheduleId.generate() for _ in range(schedule_count)]
    for sid in schedule_ids:
        group.register_schedule(sid)
    return group, schedule_ids


class TestScheduleGroupCreate:
    def test_creates_with_defaults(self) -> None:
        group = _make_group()
        assert group.agenda_templates == []
        assert group.schedule_ids == []
        assert group.template_id is None
        assert group.created_at == _NOW
        assert group.updated_at == _NOW

    def test_creates_with_agenda_templates(self) -> None:
        templates = [AgendaTemplate("Topic A"), AgendaTemplate("Topic B")]
        group = _make_group(agenda_templates=templates)
        assert group.agenda_templates == templates

    def test_creates_with_template_id(self) -> None:
        tid = TemplateId.generate()
        group = _make_group(template_id=tid)
        assert group.template_id == tid

    def test_emits_created_event(self) -> None:
        group = _make_group()
        events = group.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleGroupCreated)
        assert event.schedule_group_id == group.id
        assert event.organizer_id == group.organizer_id

    def test_collect_events_clears_list(self) -> None:
        group = _make_group()
        group.collect_events()
        assert group.collect_events() == []


class TestScheduleGroupRegisterSchedule:
    def test_register_schedule(self) -> None:
        group = _make_group()
        sid = ScheduleId.generate()
        group.register_schedule(sid)
        assert sid in group.schedule_ids

    def test_register_multiple_schedules(self) -> None:
        group = _make_group()
        sids = [ScheduleId.generate() for _ in range(3)]
        for sid in sids:
            group.register_schedule(sid)
        assert group.schedule_ids == sids

    def test_register_duplicate_schedule_is_ignored(self) -> None:
        group = _make_group()
        sid = ScheduleId.generate()
        group.register_schedule(sid)
        group.register_schedule(sid)
        assert group.schedule_ids == [sid]


class TestScheduleGroupAddAgenda:
    def test_add_agenda_to_all_schedules(self) -> None:
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        new_agendas = group.add_agenda_to_schedules(
            topic="New topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        assert len(new_agendas) == 3
        for sid in schedule_ids:
            assert len(schedules_agendas[sid]) == 1
            assert schedules_agendas[sid][0].topic == Topic("New topic")
        # Template also updated
        assert AgendaTemplate("New topic") in group.agenda_templates

    def test_add_agenda_updates_timestamp(self) -> None:
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        group.add_agenda_to_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        assert group.updated_at == _LATER

    def test_add_agenda_emits_event(self) -> None:
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        group.collect_events()  # clear creation event
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        group.add_agenda_to_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        events = group.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, AgendaAddedViaGroup)
        assert event.topic == "Topic"
        assert set(event.target_schedule_ids) == set(schedule_ids)

    def test_non_organizer_cannot_add_agenda(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        with pytest.raises(
            UnauthorizedScheduleGroupOperationError, match="Only the organizer"
        ):
            group.add_agenda_to_schedules(
                topic="Topic",
                actor_id=other,
                schedules_agendas=schedules_agendas,
                now=_LATER,
            )

    def test_add_agenda_with_zero_schedules(self) -> None:
        """0 targets: normal completion with no side effects."""
        organizer = UserId.generate()
        group = _make_group(organizer_id=organizer)

        new_agendas = group.add_agenda_to_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas={},
            now=_LATER,
        )

        assert new_agendas == []
        # Template still added even with no schedules
        assert AgendaTemplate("Topic") in group.agenda_templates

    def test_add_agenda_fails_when_schedules_agendas_missing_keys(self) -> None:
        """Adding fails if schedules_agendas misses schedule IDs."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(
            organizer_id=organizer, schedule_count=3
        )
        # Only provide 2 of 3 schedule IDs
        partial_agendas: dict[ScheduleId, list[Agenda]] = {
            schedule_ids[0]: [],
            schedule_ids[1]: [],
        }

        with pytest.raises(InconsistentScheduleAgendasError, match="missing keys"):
            group.add_agenda_to_schedules(
                topic="Topic",
                actor_id=organizer,
                schedules_agendas=partial_agendas,
                now=_LATER,
            )

        # Verify no partial mutation: no template added, timestamp unchanged
        assert group.agenda_templates == []
        assert group.updated_at == _NOW

    def test_duplicate_topic_allowed(self) -> None:
        """Duplicate agenda topics are permitted."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        group.add_agenda_to_schedules(
            topic="Same topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        group.add_agenda_to_schedules(
            topic="Same topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        for sid in schedule_ids:
            assert len(schedules_agendas[sid]) == 2
        assert group.agenda_templates.count(AgendaTemplate("Same topic")) == 2


class TestScheduleGroupRemoveAgenda:
    def test_remove_agenda_from_all_schedules(self) -> None:
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        # First add agendas
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }
        group.add_agenda_to_schedules(
            topic="To remove",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        group.collect_events()  # clear

        removed_ids = group.remove_agenda_from_schedules(
            topic="To remove",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        assert len(removed_ids) == 3
        for sid in schedule_ids:
            assert len(schedules_agendas[sid]) == 0
        assert AgendaTemplate("To remove") not in group.agenda_templates

    def test_remove_agenda_emits_event(self) -> None:
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }
        group.add_agenda_to_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        group.collect_events()  # clear

        group.remove_agenda_from_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        events = group.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, AgendaRemovedViaGroup)
        assert event.topic == "Topic"
        assert len(event.removed_agenda_ids) == 3

    def test_non_organizer_cannot_remove_agenda(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }

        with pytest.raises(
            UnauthorizedScheduleGroupOperationError, match="Only the organizer"
        ):
            group.remove_agenda_from_schedules(
                topic="Topic",
                actor_id=other,
                schedules_agendas=schedules_agendas,
                now=_LATER,
            )

    def test_remove_agenda_with_zero_schedules(self) -> None:
        """0 targets: normal completion with no side effects."""
        organizer = UserId.generate()
        group = _make_group(
            organizer_id=organizer,
            agenda_templates=[AgendaTemplate("Topic")],
        )

        removed_ids = group.remove_agenda_from_schedules(
            topic="Topic",
            actor_id=organizer,
            schedules_agendas={},
            now=_LATER,
        )

        assert removed_ids == []
        assert AgendaTemplate("Topic") not in group.agenda_templates

    def test_remove_with_comments_deletes_all(self) -> None:
        """Removing agenda also deletes associated comments."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(
            organizer_id=organizer, schedule_count=1
        )
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }
        group.add_agenda_to_schedules(
            topic="With comments",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        # Add comment to the agenda
        agenda = schedules_agendas[schedule_ids[0]][0]
        agenda.add_comment(author_id=UserId.generate(), body="A comment", now=_LATER)
        assert len(agenda.comments) == 1

        removed_ids = group.remove_agenda_from_schedules(
            topic="With comments",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        # Agenda is removed (including its comments)
        assert len(removed_ids) == 1
        assert len(schedules_agendas[schedule_ids[0]]) == 0

    def test_remove_agenda_normalizes_topic(self) -> None:
        """Removing with whitespace-padded topic matches the normalized stored topic."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(
            organizer_id=organizer, schedule_count=1
        )
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }
        group.add_agenda_to_schedules(
            topic="  目標確認  ",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        assert len(schedules_agendas[schedule_ids[0]]) == 1

        # Remove with different whitespace
        removed_ids = group.remove_agenda_from_schedules(
            topic="  目標確認  ",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        assert len(removed_ids) == 1
        assert len(schedules_agendas[schedule_ids[0]]) == 0
        assert group.agenda_templates == []

    def test_remove_agenda_fails_when_schedules_agendas_missing_keys(self) -> None:
        """Removing fails if schedules_agendas misses schedule IDs."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(
            organizer_id=organizer, schedule_count=2
        )
        group = _make_group(
            organizer_id=organizer,
            agenda_templates=[AgendaTemplate("Topic")],
        )
        sid1 = ScheduleId.generate()
        sid2 = ScheduleId.generate()
        group.register_schedule(sid1)
        group.register_schedule(sid2)

        # Only provide one of two schedule IDs
        with pytest.raises(InconsistentScheduleAgendasError, match="missing keys"):
            group.remove_agenda_from_schedules(
                topic="Topic",
                actor_id=organizer,
                schedules_agendas={sid1: []},
                now=_LATER,
            )

    def test_remove_nonexistent_topic_is_noop(self) -> None:
        """Removing a topic that has no matching template is a no-op."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(organizer_id=organizer)
        group.collect_events()  # clear

        removed_ids = group.remove_agenda_from_schedules(
            topic="Nonexistent",
            actor_id=organizer,
            schedules_agendas={sid: [] for sid in schedule_ids},
            now=_LATER,
        )

        assert removed_ids == []
        assert group.updated_at == _NOW  # timestamp not updated
        assert group.collect_events() == []  # no events emitted

    def test_remove_duplicate_removes_one_per_schedule(self) -> None:
        """When duplicate topics exist, remove only removes one per schedule."""
        organizer = UserId.generate()
        group, schedule_ids = _make_group_with_schedules(
            organizer_id=organizer, schedule_count=1
        )
        schedules_agendas: dict[ScheduleId, list[Agenda]] = {
            sid: [] for sid in schedule_ids
        }
        # Add same topic twice
        group.add_agenda_to_schedules(
            topic="Dup",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        group.add_agenda_to_schedules(
            topic="Dup",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )
        assert len(schedules_agendas[schedule_ids[0]]) == 2

        group.remove_agenda_from_schedules(
            topic="Dup",
            actor_id=organizer,
            schedules_agendas=schedules_agendas,
            now=_LATER,
        )

        # One removed, one remains
        assert len(schedules_agendas[schedule_ids[0]]) == 1
        assert group.agenda_templates.count(AgendaTemplate("Dup")) == 1


class TestScheduleGroupProperties:
    def test_agenda_templates_returns_copy(self) -> None:
        templates = [AgendaTemplate("A")]
        group = _make_group(agenda_templates=templates)
        returned = group.agenda_templates
        assert returned is not group.agenda_templates

    def test_schedule_ids_returns_copy(self) -> None:
        group = _make_group()
        group.register_schedule(ScheduleId.generate())
        returned = group.schedule_ids
        assert returned is not group.schedule_ids
