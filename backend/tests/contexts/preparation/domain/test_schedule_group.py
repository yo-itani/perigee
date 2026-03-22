from datetime import datetime

import pytest

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import (
    AgendaAddedViaGroup,
    AgendaRemovedViaGroup,
    ScheduleGroupCreated,
    ScheduleGroupRenamed,
    ScheduleRenamed,
)
from contexts.preparation.domain.exceptions import (
    InconsistentScheduleAgendasError,
    InconsistentSchedulesError,
    InvalidScheduleTitleError,
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_group import ScheduleGroup
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import ScheduleId, TemplateId
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_group(
    *,
    organizer_id: UserId | None = None,
    title: str = "Weekly 1on1",
    agenda_templates: list[AgendaTemplate] | None = None,
    template_id: TemplateId | None = None,
    now: datetime = _NOW,
) -> ScheduleGroup:
    return ScheduleGroup.create(
        organizer_id=organizer_id or UserId.generate(),
        title=title,
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


_FUTURE = datetime(2026, 4, 1, 10, 0)


def _make_child_schedule(
    *,
    organizer_id: UserId,
    counterpart_id: UserId,
    title: str = "Weekly 1on1",
) -> Schedule:
    """Create a schedule for use as a child of a ScheduleGroup."""
    return Schedule.create(
        organizer_id=organizer_id,
        counterpart_id=counterpart_id,
        scheduled_at=_FUTURE,
        requested_by=organizer_id,
        title=title,
        now=_NOW,
    )


class TestScheduleGroupTitle:
    def test_create_sets_title(self) -> None:
        group = _make_group(title="Monthly 1on1")
        assert group.title == ScheduleTitle("Monthly 1on1")

    def test_create_with_invalid_title_raises(self) -> None:
        with pytest.raises(InvalidScheduleTitleError):
            _make_group(title="")

    def test_rename(self) -> None:
        organizer = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")
        group.collect_events()

        group.rename(title="New title", actor_id=organizer, now=_LATER, schedules=[])

        assert group.title == ScheduleTitle("New title")
        assert group.updated_at == _LATER

    def test_rename_emits_event(self) -> None:
        organizer = UserId.generate()
        cp = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")
        s = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp, title="Old title"
        )
        group.register_schedule(s.id)
        group.collect_events()

        group.rename(title="New title", actor_id=organizer, now=_LATER, schedules=[s])

        events = group.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleGroupRenamed)
        assert event.schedule_group_id == group.id
        assert event.new_title == "New title"
        assert event.renamed_schedule_ids == [s.id]
        assert event.occurred_at == _LATER

    def test_rename_propagates_to_child_schedules(self) -> None:
        organizer = UserId.generate()
        cp1 = UserId.generate()
        cp2 = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")

        s1 = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp1, title="Old title"
        )
        s2 = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp2, title="Old title"
        )
        group.register_schedule(s1.id)
        group.register_schedule(s2.id)
        s1.collect_events()
        s2.collect_events()
        group.collect_events()

        group.rename(
            title="New title", actor_id=organizer, now=_LATER, schedules=[s1, s2]
        )

        assert s1.title == ScheduleTitle("New title")
        assert s2.title == ScheduleTitle("New title")
        # Each child schedule should have emitted a ScheduleRenamed event
        s1_events = s1.collect_events()
        assert len(s1_events) == 1
        assert isinstance(s1_events[0], ScheduleRenamed)
        s2_events = s2.collect_events()
        assert len(s2_events) == 1
        assert isinstance(s2_events[0], ScheduleRenamed)

    def test_rename_same_title_is_noop(self) -> None:
        organizer = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Same title")
        group.collect_events()

        group.rename(title="Same title", actor_id=organizer, now=_LATER, schedules=[])

        assert group.collect_events() == []
        assert group.updated_at == _NOW  # unchanged

    def test_rename_same_title_after_normalization_is_noop(self) -> None:
        organizer = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Same title")
        group.collect_events()

        group.rename(
            title="  Same title  ", actor_id=organizer, now=_LATER, schedules=[]
        )

        assert group.collect_events() == []
        assert group.updated_at == _NOW  # unchanged

    def test_rename_with_invalid_title_raises(self) -> None:
        organizer = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Valid title")

        with pytest.raises(InvalidScheduleTitleError):
            group.rename(title="", actor_id=organizer, now=_LATER, schedules=[])

    def test_rename_propagates_regardless_of_schedule_status(self) -> None:
        """All child schedules are renamed regardless of their status."""
        organizer = UserId.generate()
        cp = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")

        # Create a confirmed schedule
        schedule = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp, title="Old title"
        )
        schedule.confirm(actor_id=cp, now=_LATER)
        group.register_schedule(schedule.id)
        schedule.collect_events()
        group.collect_events()

        rename_time = datetime(2026, 3, 20, 12, 0)
        group.rename(
            title="New title",
            actor_id=organizer,
            now=rename_time,
            schedules=[schedule],
        )

        assert schedule.title == ScheduleTitle("New title")

    def test_non_organizer_cannot_rename(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")

        with pytest.raises(
            UnauthorizedScheduleGroupOperationError, match="Only the organizer"
        ):
            group.rename(title="New title", actor_id=other, now=_LATER, schedules=[])

    def test_rename_fails_when_schedules_missing(self) -> None:
        """Rename fails if schedules list does not cover all registered IDs."""
        organizer = UserId.generate()
        cp = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")

        s1 = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp, title="Old title"
        )
        s2_id = ScheduleId.generate()
        group.register_schedule(s1.id)
        group.register_schedule(s2_id)
        group.collect_events()

        with pytest.raises(InconsistentSchedulesError, match="do not match"):
            group.rename(
                title="New title",
                actor_id=organizer,
                now=_LATER,
                schedules=[s1],  # missing s2
            )

        # Verify no partial mutation
        assert group.title == ScheduleTitle("Old title")
        assert group.updated_at == _NOW

    def test_rename_fails_when_extra_schedules_provided(self) -> None:
        """Rename fails if schedules list contains IDs not registered."""
        organizer = UserId.generate()
        cp = UserId.generate()
        group = _make_group(organizer_id=organizer, title="Old title")

        s1 = _make_child_schedule(
            organizer_id=organizer, counterpart_id=cp, title="Old title"
        )
        group.register_schedule(s1.id)

        extra = _make_child_schedule(
            organizer_id=organizer,
            counterpart_id=UserId.generate(),
            title="Old title",
        )
        group.collect_events()

        with pytest.raises(InconsistentSchedulesError, match="do not match"):
            group.rename(
                title="New title",
                actor_id=organizer,
                now=_LATER,
                schedules=[s1, extra],
            )
