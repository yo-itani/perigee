from datetime import datetime

import pytest

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.events import TemplateSaved
from contexts.preparation.domain.exceptions import (
    InvalidTemplateNameError,
    UnauthorizedScheduleGroupOperationError,
)
from contexts.preparation.domain.template import Template
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_template(
    *,
    organizer_id: UserId | None = None,
    name: str = "Monthly 1on1",
    default_counterparts: list[UserId] | None = None,
    agenda_templates: list[AgendaTemplate] | None = None,
    now: datetime = _NOW,
) -> Template:
    return Template.create(
        organizer_id=organizer_id or UserId.generate(),
        name=name,
        default_counterparts=default_counterparts,
        agenda_templates=agenda_templates,
        now=now,
    )


class TestTemplateCreate:
    def test_creates_with_defaults(self) -> None:
        tmpl = _make_template()
        assert tmpl.name == "Monthly 1on1"
        assert tmpl.default_counterparts == []
        assert tmpl.agenda_templates == []
        assert tmpl.created_at == _NOW

    def test_creates_with_counterparts_and_agenda_templates(self) -> None:
        cps = [UserId.generate(), UserId.generate()]
        ats = [AgendaTemplate("Topic A"), AgendaTemplate("Topic B")]
        tmpl = _make_template(default_counterparts=cps, agenda_templates=ats)
        assert tmpl.default_counterparts == cps
        assert tmpl.agenda_templates == ats

    def test_name_strips_whitespace(self) -> None:
        tmpl = _make_template(name="  Padded Name  ")
        assert tmpl.name == "Padded Name"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not be empty"):
            _make_template(name="")

    def test_whitespace_only_name_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not be empty"):
            _make_template(name="   ")

    def test_name_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not exceed"):
            _make_template(name="a" * 101)

    def test_name_exactly_max_length_is_valid(self) -> None:
        tmpl = _make_template(name="a" * 100)
        assert len(tmpl.name) == 100

    def test_emits_template_saved_event(self) -> None:
        tmpl = _make_template()
        events = tmpl.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TemplateSaved)
        assert event.template_id == tmpl.id
        assert event.name == "Monthly 1on1"

    def test_collect_events_clears_list(self) -> None:
        tmpl = _make_template()
        tmpl.collect_events()
        assert tmpl.collect_events() == []


class TestTemplateUpdate:
    def test_update_all_fields(self) -> None:
        organizer = UserId.generate()
        tmpl = _make_template(organizer_id=organizer)
        new_cps = [UserId.generate()]
        new_ats = [AgendaTemplate("New topic")]

        tmpl.update(
            actor_id=organizer,
            name="Updated Name",
            default_counterparts=new_cps,
            agenda_templates=new_ats,
            now=_LATER,
        )

        assert tmpl.name == "Updated Name"
        assert tmpl.default_counterparts == new_cps
        assert tmpl.agenda_templates == new_ats
        assert tmpl.updated_at == _LATER

    def test_update_emits_event(self) -> None:
        organizer = UserId.generate()
        tmpl = _make_template(organizer_id=organizer)
        tmpl.collect_events()  # clear

        tmpl.update(
            actor_id=organizer,
            name="New Name",
            default_counterparts=[],
            agenda_templates=[],
            now=_LATER,
        )

        events = tmpl.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TemplateSaved)
        assert event.name == "New Name"

    def test_non_organizer_cannot_update(self) -> None:
        organizer = UserId.generate()
        other = UserId.generate()
        tmpl = _make_template(organizer_id=organizer)

        with pytest.raises(
            UnauthorizedScheduleGroupOperationError, match="Only the organizer"
        ):
            tmpl.update(
                actor_id=other,
                name="New Name",
                default_counterparts=[],
                agenda_templates=[],
                now=_LATER,
            )

    def test_update_with_invalid_name_raises(self) -> None:
        organizer = UserId.generate()
        tmpl = _make_template(organizer_id=organizer)

        with pytest.raises(InvalidTemplateNameError, match="must not be empty"):
            tmpl.update(
                actor_id=organizer,
                name="",
                default_counterparts=[],
                agenda_templates=[],
                now=_LATER,
            )


class TestTemplateProperties:
    def test_default_counterparts_returns_copy(self) -> None:
        cps = [UserId.generate()]
        tmpl = _make_template(default_counterparts=cps)
        returned = tmpl.default_counterparts
        assert returned is not tmpl.default_counterparts

    def test_agenda_templates_returns_copy(self) -> None:
        ats = [AgendaTemplate("A")]
        tmpl = _make_template(agenda_templates=ats)
        returned = tmpl.agenda_templates
        assert returned is not tmpl.agenda_templates
