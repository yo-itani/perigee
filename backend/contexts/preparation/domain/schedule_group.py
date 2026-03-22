from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.preparation.domain.agenda import Agenda
from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import (
    AgendaAddedViaGroup,
    AgendaRemovedViaGroup,
    ScheduleGroupCreated,
    ScheduleGroupRenamed,
)
from contexts.preparation.domain.exceptions import (
    InconsistentScheduleAgendasError,
    InconsistentSchedulesError,
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.topic import Topic
from contexts.preparation.domain.value_objects import (
    AgendaId,
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
from shared.domain.value_objects import UserId

type _ScheduleGroupEvent = (
    ScheduleGroupCreated
    | ScheduleGroupRenamed
    | AgendaAddedViaGroup
    | AgendaRemovedViaGroup
)


@dataclass
class ScheduleGroup:
    """Aggregate root: a batch management unit for 1-on-1 schedules.

    Created by an organizer to register schedules for multiple counterparts
    at once. Holds agenda templates that are expanded into Agenda entities
    when individual Schedules are created.

    Business rules:
    - Only the organizer who created the group can operate on it.
    - Agenda add/remove propagates to all associated Schedules.
    - Agenda edit (topic change) is prohibited; use delete + re-add.
    - Duplicate topics are allowed.
    - Bulk operations with 0 targets succeed with no side effects.
    - Failures during bulk operations roll back all changes
      (synchronous transaction).
    """

    id: ScheduleGroupId
    organizer_id: UserId
    template_id: TemplateId | None
    _title: ScheduleTitle
    _agenda_templates: list[AgendaTemplate]
    _schedule_ids: list[ScheduleId]
    created_at: datetime
    _updated_at: datetime
    _events: list[_ScheduleGroupEvent] = field(default_factory=list, repr=False)

    @property
    def title(self) -> ScheduleTitle:
        return self._title

    @property
    def agenda_templates(self) -> list[AgendaTemplate]:
        return list(self._agenda_templates)

    @property
    def schedule_ids(self) -> list[ScheduleId]:
        return list(self._schedule_ids)

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def collect_events(self) -> list[_ScheduleGroupEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        *,
        organizer_id: UserId,
        title: str,
        agenda_templates: list[AgendaTemplate] | None = None,
        template_id: TemplateId | None = None,
        now: datetime | None = None,
    ) -> ScheduleGroup:
        """Create a new ScheduleGroup.

        Args:
            organizer_id: The organizer creating this group.
            title: The title of the schedule group.
            agenda_templates: Initial agenda templates (optional).
            template_id: Source template ID if created from a template.
            now: Current time (defaults to UTC now).

        Raises:
            InvalidScheduleTitleError: If title fails validation.
        """
        ts = now or datetime.now(UTC)
        schedule_title = ScheduleTitle(title)
        group_id = ScheduleGroupId.generate()
        group = ScheduleGroup(
            id=group_id,
            organizer_id=organizer_id,
            template_id=template_id,
            _title=schedule_title,
            _agenda_templates=list(agenda_templates) if agenda_templates else [],
            _schedule_ids=[],
            created_at=ts,
            _updated_at=ts,
        )
        group._events.append(
            ScheduleGroupCreated(
                schedule_group_id=group_id,
                organizer_id=organizer_id,
                template_id=template_id,
                occurred_at=ts,
            )
        )
        return group

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def rename(
        self,
        *,
        title: str,
        actor_id: UserId,
        now: datetime,
        schedules: list[Schedule],
    ) -> None:
        """Rename the schedule group and propagate to all child schedules.

        No-op if the new title is the same as the current title
        (after normalization).

        All child schedules are renamed regardless of their status.

        Args:
            title: The new title for the group and its schedules.
            actor_id: The user performing the operation (must be organizer).
            now: Current time.
            schedules: All child Schedule entities to propagate the rename to.
                Must match the registered schedule IDs exactly.

        Raises:
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
            InconsistentSchedulesError: If schedules do not match the
                registered schedule IDs.
            InvalidScheduleTitleError: If title fails validation.
        """
        self._assert_organizer(actor_id)
        self._assert_schedules_complete(schedules)

        new_title = ScheduleTitle(title)
        if new_title == self._title:
            return
        self._title = new_title
        self._updated_at = now

        for schedule in schedules:
            schedule.rename(new_title=new_title.value, now=now)

        self._events.append(
            ScheduleGroupRenamed(
                schedule_group_id=self.id,
                new_title=new_title.value,
                renamed_schedule_ids=list(self._schedule_ids),
                occurred_at=now,
            )
        )

    def register_schedule(self, schedule_id: ScheduleId) -> None:
        """Register a schedule as belonging to this group.

        Duplicate registration of the same ScheduleId is silently ignored.
        """
        if schedule_id not in self._schedule_ids:
            self._schedule_ids.append(schedule_id)

    def add_agenda_to_schedules(
        self,
        *,
        topic: str,
        actor_id: UserId,
        schedules_agendas: dict[ScheduleId, list[Agenda]],
        now: datetime,
    ) -> list[Agenda]:
        """Add an agenda topic to all associated schedules.

        Creates a new AgendaTemplate and expands it into Agenda entities
        for each schedule. Returns the newly created Agenda entities.

        Args:
            topic: The agenda topic to add.
            actor_id: The user performing the operation (must be organizer).
            schedules_agendas: Mutable agenda lists keyed by schedule ID.
                New agendas are appended to each list. Must contain keys
                for all registered schedule IDs.
            now: Current time.

        Returns:
            List of newly created Agenda entities.

        Raises:
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
            InconsistentScheduleAgendasError: If schedules_agendas is
                missing keys for registered schedule IDs.
        """
        self._assert_organizer(actor_id)
        self._assert_schedules_agendas_complete(schedules_agendas)

        agenda_template = AgendaTemplate(topic)
        self._agenda_templates.append(agenda_template)
        self._updated_at = now

        new_agendas: list[Agenda] = []
        for schedule_id in self._schedule_ids:
            agenda = Agenda.create(
                schedule_id=schedule_id,
                topic=agenda_template.topic.value,
                added_by=actor_id,
                now=now,
            )
            new_agendas.append(agenda)
            schedules_agendas[schedule_id].append(agenda)

        self._events.append(
            AgendaAddedViaGroup(
                schedule_group_id=self.id,
                topic=agenda_template.topic.value,
                target_schedule_ids=list(self._schedule_ids),
                occurred_at=now,
            )
        )
        return new_agendas

    def remove_agenda_from_schedules(
        self,
        *,
        topic: str,
        actor_id: UserId,
        schedules_agendas: dict[ScheduleId, list[Agenda]],
        now: datetime,
    ) -> list[AgendaId]:
        """Remove an agenda topic from all associated schedules.

        Removes the first matching AgendaTemplate and physically deletes
        all matching Agenda entities (including their comments).

        Args:
            topic: The agenda topic to remove.
            actor_id: The user performing the operation (must be organizer).
            schedules_agendas: Mutable agenda lists keyed by schedule ID.
                Matching agendas are removed from each list.
            now: Current time.

        Returns:
            List of removed Agenda IDs.

        Raises:
            UnauthorizedScheduleGroupOperationError: If actor is not the
                organizer.
            InconsistentScheduleAgendasError: If schedules_agendas is
                missing keys for registered schedule IDs.
        """
        self._assert_organizer(actor_id)
        self._assert_schedules_agendas_complete(schedules_agendas)

        normalized_topic = Topic(topic).value

        # Remove first matching template; if none found, this is a no-op.
        found = False
        for i, tmpl in enumerate(self._agenda_templates):
            if tmpl.topic.value == normalized_topic:
                self._agenda_templates.pop(i)
                found = True
                break

        if not found:
            return []

        self._updated_at = now

        removed_ids: list[AgendaId] = []
        for schedule_id in self._schedule_ids:
            agendas = schedules_agendas[schedule_id]
            to_remove: list[int] = []
            for idx, agenda in enumerate(agendas):
                if agenda.topic.value == normalized_topic:
                    removed_ids.append(agenda.id)
                    to_remove.append(idx)
                    break  # Remove one matching agenda per schedule
            for idx in reversed(to_remove):
                agendas.pop(idx)

        self._events.append(
            AgendaRemovedViaGroup(
                schedule_group_id=self.id,
                topic=normalized_topic,
                removed_agenda_ids=removed_ids,
                occurred_at=now,
            )
        )
        return removed_ids

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_organizer(self, actor_id: UserId) -> None:
        if actor_id != self.organizer_id:
            raise UnauthorizedScheduleGroupOperationError(
                "Only the organizer can operate on this schedule group."
            )

    def _assert_schedules_complete(self, schedules: list[Schedule]) -> None:
        """Verify schedules list matches all registered schedule IDs."""
        provided = {s.id for s in schedules}
        expected = set(self._schedule_ids)
        if provided != expected:
            raise InconsistentSchedulesError(
                f"Provided schedule IDs {provided} do not match "
                f"registered schedule IDs {expected}."
            )

    def _assert_schedules_agendas_complete(
        self, schedules_agendas: dict[ScheduleId, list[Agenda]]
    ) -> None:
        """Verify schedules_agendas has keys for all schedule IDs."""
        missing = set(self._schedule_ids) - schedules_agendas.keys()
        if missing:
            raise InconsistentScheduleAgendasError(
                f"schedules_agendas is missing keys for schedule IDs: {missing}"
            )
