"""Tests for Schedule <-> ScheduleRow mapping functions.

These tests verify that domain entities can be correctly converted to ORM rows
and back without data loss. No database is required.
"""

from datetime import datetime

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import (
    ConfirmationResolution,
    ScheduleStatus,
)
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    _entity_to_row,
    _row_to_entity,
)
from shared.domain.value_objects import UserId

_NOW = datetime(2026, 3, 20, 10, 0)
_FUTURE = datetime(2026, 4, 1, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_schedule() -> Schedule:
    """Create a simple requested schedule for mapping tests."""
    org = UserId.generate()
    cp = UserId.generate()
    return Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=_FUTURE,
        requested_by=org,
        now=_NOW,
    )


def _make_confirmed_schedule() -> Schedule:
    """Create a confirmed schedule for mapping tests."""
    org = UserId.generate()
    cp = UserId.generate()
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=_FUTURE,
        requested_by=org,
        now=_NOW,
    )
    schedule.confirm(actor_id=cp, now=_LATER)
    return schedule


class TestEntityToRowMapping:
    def test_schedule_fields_are_mapped(self) -> None:
        schedule = _make_schedule()
        row = _entity_to_row(schedule)

        assert row.id == str(schedule.id.value)
        assert row.organizer_id == str(schedule.organizer_id.value)
        assert row.counterpart_id == str(schedule.counterpart_id.value)
        assert row.scheduled_at == schedule.scheduled_at
        assert row.status == schedule.status.value
        assert row.created_at == schedule.created_at
        assert row.updated_at == schedule.updated_at

    def test_confirmation_requests_are_mapped(self) -> None:
        schedule = _make_schedule()
        row = _entity_to_row(schedule)

        assert len(row.confirmation_requests) == 1
        cr_row = row.confirmation_requests[0]
        cr = schedule.confirmation_requests[0]
        assert cr_row.id == str(cr.id.value)
        assert cr_row.schedule_id == str(schedule.id.value)
        assert cr_row.request_type == cr.request_type.value
        assert cr_row.requested_by == str(cr.requested_by.value)
        assert cr_row.proposed_at == cr.proposed_at
        assert cr_row.resolution == cr.resolution.value
        assert cr_row.resolved_by is None

    def test_confirmed_schedule_maps_resolved_by(self) -> None:
        schedule = _make_confirmed_schedule()
        row = _entity_to_row(schedule)

        approved = [
            cr for cr in row.confirmation_requests if cr.resolution == "approved"
        ]
        assert len(approved) == 1
        assert approved[0].resolved_by is not None


class TestRowToEntityMapping:
    def test_roundtrip_preserves_schedule_fields(self) -> None:
        original = _make_schedule()
        original.collect_events()  # clear events before roundtrip

        row = _entity_to_row(original)
        restored = _row_to_entity(row)

        assert restored.id == original.id
        assert restored.organizer_id == original.organizer_id
        assert restored.counterpart_id == original.counterpart_id
        assert restored.scheduled_at == original.scheduled_at
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at

    def test_roundtrip_preserves_confirmation_requests(self) -> None:
        original = _make_schedule()
        original.collect_events()

        row = _entity_to_row(original)
        restored = _row_to_entity(row)

        orig_count = len(original.confirmation_requests)
        assert len(restored.confirmation_requests) == orig_count
        orig_cr = original.confirmation_requests[0]
        rest_cr = restored.confirmation_requests[0]
        assert rest_cr.id == orig_cr.id
        assert rest_cr.request_type == orig_cr.request_type
        assert rest_cr.requested_by == orig_cr.requested_by
        assert rest_cr.proposed_at == orig_cr.proposed_at
        assert rest_cr.resolution == orig_cr.resolution
        assert rest_cr.resolved_by == orig_cr.resolved_by

    def test_roundtrip_confirmed_schedule(self) -> None:
        original = _make_confirmed_schedule()
        original.collect_events()

        row = _entity_to_row(original)
        restored = _row_to_entity(row)

        assert restored.status == ScheduleStatus.CONFIRMED
        assert len(restored.confirmation_requests) == 1
        cr = restored.confirmation_requests[0]
        assert cr.resolution == ConfirmationResolution.APPROVED

    def test_roundtrip_with_multiple_confirmation_requests(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=_FUTURE,
            requested_by=org,
            now=_NOW,
        )
        schedule.confirm(actor_id=cp, now=_LATER)
        new_time = datetime(2026, 5, 1, 10, 0)
        schedule.reschedule(actor_id=org, new_proposed_at=new_time, now=_LATER)
        schedule.collect_events()

        row = _entity_to_row(schedule)
        restored = _row_to_entity(row)

        assert len(restored.confirmation_requests) == 2
        assert restored.status == ScheduleStatus.REQUESTED

    def test_restored_entity_has_no_events(self) -> None:
        """Entities loaded from DB should have an empty events list."""
        original = _make_schedule()
        row = _entity_to_row(original)
        restored = _row_to_entity(row)

        events = restored.collect_events()
        assert events == []
