from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import TemplateSaved
from contexts.preparation.domain.exceptions import (
    InvalidTemplateNameError,
    UnauthorizedTemplateOperationError,
)
from contexts.preparation.domain.value_objects import TemplateId
from shared.domain.value_objects import UserId

_TEMPLATE_NAME_MAX_LENGTH = 100


@dataclass
class Template:
    """Entity: a reusable preset for ScheduleGroup creation.

    Templates are created from within the ScheduleGroup creation flow
    ("save as template"). They hold default counterparts and agenda
    templates that are copied into a new ScheduleGroup.

    Domain logic is thin (master-data-like).
    """

    id: TemplateId
    organizer_id: UserId
    _name: str
    _default_counterparts: list[UserId]
    _agenda_templates: list[AgendaTemplate]
    created_at: datetime
    _updated_at: datetime
    _events: list[TemplateSaved] = field(default_factory=list, repr=False)

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_counterparts(self) -> list[UserId]:
        return list(self._default_counterparts)

    @property
    def agenda_templates(self) -> list[AgendaTemplate]:
        return list(self._agenda_templates)

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def collect_events(self) -> list[TemplateSaved]:
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
        name: str,
        default_counterparts: list[UserId] | None = None,
        agenda_templates: list[AgendaTemplate] | None = None,
        now: datetime | None = None,
    ) -> Template:
        """Create a new template.

        Args:
            organizer_id: The organizer who owns this template.
            name: Display name for the template.
            default_counterparts: Default counterpart user IDs.
            agenda_templates: Default agenda templates.
            now: Current time (defaults to UTC now).

        Raises:
            InvalidTemplateNameError: If name is empty or too long.
        """
        ts = now or datetime.now(UTC)
        validated_name = _validate_template_name(name)
        template_id = TemplateId.generate()

        template = Template(
            id=template_id,
            organizer_id=organizer_id,
            _name=validated_name,
            _default_counterparts=list(default_counterparts)
            if default_counterparts
            else [],
            _agenda_templates=list(agenda_templates) if agenda_templates else [],
            created_at=ts,
            _updated_at=ts,
        )
        template._events.append(
            TemplateSaved(
                template_id=template_id,
                name=validated_name,
                organizer_id=organizer_id,
                occurred_at=ts,
            )
        )
        return template

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        actor_id: UserId,
        name: str,
        default_counterparts: list[UserId],
        agenda_templates: list[AgendaTemplate],
        now: datetime,
    ) -> None:
        """Update template contents.

        Only the owning organizer can update.

        Raises:
            UnauthorizedTemplateOperationError: If actor is not the
                organizer.
            InvalidTemplateNameError: If name is empty or too long.
        """
        if actor_id != self.organizer_id:
            raise UnauthorizedTemplateOperationError(
                "Only the organizer can update this template."
            )
        validated_name = _validate_template_name(name)
        self._name = validated_name
        self._default_counterparts = list(default_counterparts)
        self._agenda_templates = list(agenda_templates)
        self._updated_at = now
        self._events.append(
            TemplateSaved(
                template_id=self.id,
                name=validated_name,
                organizer_id=self.organizer_id,
                occurred_at=now,
            )
        )


def _validate_template_name(name: str) -> str:
    """Validate and normalize a template name."""
    stripped = name.strip()
    if not stripped:
        raise InvalidTemplateNameError("Template name must not be empty.")
    if len(stripped) > _TEMPLATE_NAME_MAX_LENGTH:
        raise InvalidTemplateNameError(
            f"Template name must not exceed {_TEMPLATE_NAME_MAX_LENGTH} characters."
        )
    return stripped
