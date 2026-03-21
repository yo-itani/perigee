from datetime import datetime

import pytest

from contexts.preparation.domain.events import (
    ScheduleCancelled,
    ScheduleConfirmed,
    ScheduleCreated,
    ScheduleRejected,
    ScheduleRescheduled,
)
from contexts.preparation.domain.exceptions import (
    InvalidScheduleOperationError,
    NoPendingConfirmationRequestError,
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.value_objects import (
    ConfirmationRequestType,
    ConfirmationResolution,
    ScheduleStatus,
)
from shared.domain.value_objects import UserId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 20, 10, 0)
_FUTURE = datetime(2026, 4, 1, 10, 0)
_FUTURE2 = datetime(2026, 4, 2, 10, 0)
_LATER = datetime(2026, 3, 20, 11, 0)


def _make_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    scheduled_at: datetime = _FUTURE,
    requested_by: UserId | None = None,
    now: datetime = _NOW,
) -> Schedule:
    """Create a schedule with sensible defaults (organizer creates it)."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    return Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=scheduled_at,
        requested_by=requested_by or org,
        now=now,
    )


def _make_confirmed_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
    scheduled_at: datetime = _FUTURE,
    now: datetime = _NOW,
) -> Schedule:
    """Create a confirmed schedule."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=scheduled_at,
        requested_by=org,
        now=now,
    )
    schedule.confirm(actor_id=cp, now=_LATER)
    schedule.collect_events()  # clear events
    return schedule


def _make_cancelled_schedule(
    *,
    organizer_id: UserId | None = None,
    counterpart_id: UserId | None = None,
) -> Schedule:
    """Create a cancelled schedule."""
    org = organizer_id or UserId.generate()
    cp = counterpart_id or UserId.generate()
    schedule = Schedule.create(
        organizer_id=org,
        counterpart_id=cp,
        scheduled_at=_FUTURE,
        requested_by=org,
        now=_NOW,
    )
    schedule.cancel(actor_id=org, now=_LATER)
    schedule.collect_events()
    return schedule


# ===========================================================================
# Schedule Creation
# ===========================================================================


class TestScheduleCreate:
    def test_creates_requested_with_creation_confirmation(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)

        assert schedule.status == ScheduleStatus.REQUESTED
        assert schedule.organizer_id == org
        assert schedule.counterpart_id == cp
        assert schedule.scheduled_at == _FUTURE
        reqs = schedule.confirmation_requests
        assert len(reqs) == 1
        assert reqs[0].request_type == ConfirmationRequestType.CREATION
        assert reqs[0].resolution == ConfirmationResolution.PENDING
        assert reqs[0].requested_by == org

    def test_emits_schedule_created_event(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=_FUTURE,
            requested_by=org,
            now=_NOW,
        )
        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleCreated)
        assert event.schedule_id == schedule.id
        assert event.organizer_id == org
        assert event.counterpart_id == cp
        assert event.scheduled_at == _FUTURE
        assert event.requested_by == org
        assert event.occurred_at == _NOW

    def test_counterpart_can_create(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=_FUTURE,
            requested_by=cp,
            now=_NOW,
        )
        assert schedule.confirmation_requests[0].requested_by == cp

    def test_past_datetime_raises_error(self) -> None:
        past = datetime(2020, 1, 1, 0, 0)
        with pytest.raises(InvalidScheduleOperationError, match="past"):
            _make_schedule(scheduled_at=past)

    def test_same_datetime_as_now_is_allowed(self) -> None:
        now = datetime(2026, 3, 20, 10, 0)
        schedule = _make_schedule(scheduled_at=now, now=now)
        assert schedule.scheduled_at == now

    def test_same_user_raises_error(self) -> None:
        user = UserId.generate()
        with pytest.raises(InvalidScheduleOperationError, match="different users"):
            Schedule.create(
                organizer_id=user,
                counterpart_id=user,
                scheduled_at=_FUTURE,
                requested_by=user,
                now=_NOW,
            )

    def test_non_participant_cannot_create(self) -> None:
        other = UserId.generate()
        with pytest.raises(UnauthorizedScheduleOperationError):
            Schedule.create(
                organizer_id=UserId.generate(),
                counterpart_id=UserId.generate(),
                scheduled_at=_FUTURE,
                requested_by=other,
                now=_NOW,
            )

    def test_sets_timestamps(self) -> None:
        schedule = _make_schedule(now=_NOW)
        assert schedule.created_at == _NOW
        assert schedule.updated_at == _NOW

    def test_collect_events_clears_list(self) -> None:
        schedule = _make_schedule()
        events = schedule.collect_events()
        assert len(events) == 1
        assert schedule.collect_events() == []


# ===========================================================================
# Confirm
# ===========================================================================


class TestScheduleConfirm:
    def test_counterpart_confirms_creation(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        schedule.collect_events()

        schedule.confirm(actor_id=cp, now=_LATER)

        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.scheduled_at == _FUTURE
        assert schedule.updated_at == _LATER
        reqs = schedule.confirmation_requests
        assert reqs[0].resolution == ConfirmationResolution.APPROVED
        assert reqs[0].resolved_by == cp

    def test_emits_schedule_confirmed_event(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        schedule.collect_events()

        schedule.confirm(actor_id=cp, now=_LATER)

        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleConfirmed)
        assert event.confirmed_by == cp
        assert event.is_auto is False
        assert event.scheduled_at == _FUTURE

    def test_requester_cannot_self_confirm(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)

        with pytest.raises(UnauthorizedScheduleOperationError, match="own request"):
            schedule.confirm(actor_id=org, now=_LATER)

    def test_confirmed_schedule_has_no_pending(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(NoPendingConfirmationRequestError):
            schedule.confirm(actor_id=org, now=_LATER)

    def test_cancelled_schedule_raises_error(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_cancelled_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(ScheduleAlreadyCancelledError):
            schedule.confirm(actor_id=cp, now=_LATER)

    def test_non_participant_cannot_confirm(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        other = UserId.generate()

        with pytest.raises(UnauthorizedScheduleOperationError):
            schedule.confirm(actor_id=other, now=_LATER)

    def test_confirm_reschedule_updates_scheduled_at(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)
        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)
        schedule.collect_events()

        confirm_time = datetime(2026, 3, 20, 12, 0)
        schedule.confirm(actor_id=cp, now=confirm_time)

        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.scheduled_at == _FUTURE2


# ===========================================================================
# Reject
# ===========================================================================


class TestScheduleReject:
    def test_reject_reschedule_reverts_to_confirmed(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)
        original_scheduled_at = schedule.scheduled_at
        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)
        schedule.collect_events()

        reject_time = datetime(2026, 3, 20, 12, 0)
        schedule.reject(actor_id=cp, now=reject_time)

        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.scheduled_at == original_scheduled_at

    def test_reject_reschedule_emits_schedule_rejected(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)
        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)
        schedule.collect_events()

        reject_time = datetime(2026, 3, 20, 12, 0)
        schedule.reject(actor_id=cp, now=reject_time)

        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleRejected)
        assert event.rejected_by == cp

    def test_reject_creation_cancels_schedule(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        schedule.reject(actor_id=cp, now=_LATER)

        assert schedule.status == ScheduleStatus.CANCELLED

    def test_reject_creation_emits_schedule_cancelled(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        schedule.reject(actor_id=cp, now=_LATER)

        events = schedule.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ScheduleCancelled)
        assert events[0].cancelled_by == cp

    def test_requester_cannot_self_reject(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)

        with pytest.raises(UnauthorizedScheduleOperationError, match="own request"):
            schedule.reject(actor_id=org, now=_LATER)

    def test_cancelled_schedule_raises_error(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_cancelled_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(ScheduleAlreadyCancelledError):
            schedule.reject(actor_id=cp, now=_LATER)

    def test_confirmed_without_pending_raises_error(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(NoPendingConfirmationRequestError):
            schedule.reject(actor_id=org, now=_LATER)

    def test_reject_reschedule_never_confirmed_cancels(self) -> None:
        """Reject reschedule when schedule was never confirmed (no approved request).

        Flow: create(org) -> counterpart reschedules (rejects creation) ->
        organizer rejects reschedule -> should cancel (not revert to Confirmed).
        """
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        # Counterpart reschedules, which rejects the pending creation request
        schedule.reschedule(actor_id=cp, new_proposed_at=_FUTURE2, now=_LATER)
        schedule.collect_events()

        # Organizer rejects the reschedule; no request was ever approved
        reject_time = datetime(2026, 3, 20, 12, 0)
        schedule.reject(actor_id=org, now=reject_time)

        assert schedule.status == ScheduleStatus.CANCELLED

    def test_reject_reschedule_never_confirmed_emits_cancelled(self) -> None:
        """Rejecting reschedule when never confirmed emits ScheduleCancelled."""
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        schedule.reschedule(actor_id=cp, new_proposed_at=_FUTURE2, now=_LATER)
        schedule.collect_events()

        reject_time = datetime(2026, 3, 20, 12, 0)
        schedule.reject(actor_id=org, now=reject_time)

        events = schedule.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ScheduleCancelled)
        assert events[0].cancelled_by == org


# ===========================================================================
# Reschedule
# ===========================================================================


class TestScheduleReschedule:
    def test_reschedule_confirmed_creates_new_request(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)

        assert schedule.status == ScheduleStatus.REQUESTED
        # scheduled_at should NOT change until confirmed
        assert schedule.scheduled_at == _FUTURE
        reqs = schedule.confirmation_requests
        assert len(reqs) == 2  # original creation + reschedule
        latest = reqs[-1]
        assert latest.request_type == ConfirmationRequestType.RESCHEDULE
        assert latest.resolution == ConfirmationResolution.PENDING
        assert latest.requested_by == org
        assert latest.proposed_at == _FUTURE2

    def test_reschedule_emits_event(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)

        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleRescheduled)
        assert event.new_proposed_at == _FUTURE2
        assert event.requested_by == org

    def test_same_requester_supersedes_existing_pending(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)

        reqs = schedule.confirmation_requests
        assert reqs[0].resolution == ConfirmationResolution.SUPERSEDED
        assert reqs[1].resolution == ConfirmationResolution.PENDING
        assert reqs[1].requested_by == org

    def test_counterpart_rejects_existing_pending(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)
        schedule.collect_events()

        schedule.reschedule(actor_id=cp, new_proposed_at=_FUTURE2, now=_LATER)

        reqs = schedule.confirmation_requests
        assert reqs[0].resolution == ConfirmationResolution.REJECTED
        assert reqs[0].resolved_by == cp
        assert reqs[1].resolution == ConfirmationResolution.PENDING
        assert reqs[1].requested_by == cp

    def test_cancelled_schedule_raises_error(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_cancelled_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(ScheduleAlreadyCancelledError):
            schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=_LATER)

    def test_non_participant_cannot_reschedule(self) -> None:
        schedule = _make_confirmed_schedule()
        other = UserId.generate()

        with pytest.raises(UnauthorizedScheduleOperationError):
            schedule.reschedule(actor_id=other, new_proposed_at=_FUTURE2, now=_LATER)


# ===========================================================================
# Cancel
# ===========================================================================


class TestScheduleCancel:
    def test_cancel_confirmed_schedule(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        cancel_time = datetime(2026, 3, 20, 12, 0)
        schedule.cancel(actor_id=cp, now=cancel_time)

        assert schedule.status == ScheduleStatus.CANCELLED
        assert schedule.updated_at == cancel_time

    def test_cancel_emits_schedule_cancelled_event(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_confirmed_schedule(organizer_id=org, counterpart_id=cp)

        cancel_time = datetime(2026, 3, 20, 12, 0)
        schedule.cancel(actor_id=cp, now=cancel_time)

        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleCancelled)
        assert event.cancelled_by == cp

    def test_cancel_already_cancelled_raises_error(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_cancelled_schedule(organizer_id=org, counterpart_id=cp)

        with pytest.raises(ScheduleAlreadyCancelledError):
            schedule.cancel(actor_id=org, now=_LATER)

    def test_non_participant_cannot_cancel(self) -> None:
        schedule = _make_confirmed_schedule()
        other = UserId.generate()

        with pytest.raises(UnauthorizedScheduleOperationError):
            schedule.cancel(actor_id=other, now=_LATER)

    def test_cancel_requested_supersedes_pending(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp, requested_by=org)

        schedule.cancel(actor_id=org, now=_LATER)

        assert schedule.status == ScheduleStatus.CANCELLED
        reqs = schedule.confirmation_requests
        assert reqs[0].resolution == ConfirmationResolution.SUPERSEDED


# ===========================================================================
# Auto-confirm
# ===========================================================================


class TestScheduleAutoConfirm:
    def test_auto_confirm_requested_schedule(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        schedule.collect_events()

        schedule.auto_confirm(now=_LATER)

        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.scheduled_at == _FUTURE
        reqs = schedule.confirmation_requests
        assert reqs[0].resolution == ConfirmationResolution.APPROVED
        assert reqs[0].resolved_by is None

    def test_auto_confirm_emits_event_with_is_auto(self) -> None:
        org = UserId.generate()
        cp = UserId.generate()
        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        schedule.collect_events()

        schedule.auto_confirm(now=_LATER)

        events = schedule.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ScheduleConfirmed)
        assert event.is_auto is True
        assert event.confirmed_by is None

    def test_auto_confirm_confirmed_is_idempotent(self) -> None:
        schedule = _make_confirmed_schedule()

        schedule.auto_confirm(now=_LATER)

        # No events, no error
        assert schedule.collect_events() == []
        assert schedule.status == ScheduleStatus.CONFIRMED

    def test_auto_confirm_cancelled_raises_error(self) -> None:
        schedule = _make_cancelled_schedule()

        with pytest.raises(ScheduleAlreadyCancelledError):
            schedule.auto_confirm(now=_LATER)


# ===========================================================================
# Aggregate Invariants
# ===========================================================================


class TestAggregateInvariants:
    def test_requested_has_exactly_one_pending(self) -> None:
        schedule = _make_schedule()
        pending = [
            r
            for r in schedule.confirmation_requests
            if r.resolution == ConfirmationResolution.PENDING
        ]
        assert len(pending) == 1

    def test_confirmed_has_no_pending(self) -> None:
        schedule = _make_confirmed_schedule()
        pending = [
            r
            for r in schedule.confirmation_requests
            if r.resolution == ConfirmationResolution.PENDING
        ]
        assert len(pending) == 0

    def test_cancelled_has_no_pending(self) -> None:
        schedule = _make_cancelled_schedule()
        pending = [
            r
            for r in schedule.confirmation_requests
            if r.resolution == ConfirmationResolution.PENDING
        ]
        assert len(pending) == 0

    def test_confirmation_requests_never_empty(self) -> None:
        schedule = _make_schedule()
        assert len(schedule.confirmation_requests) >= 1

        confirmed = _make_confirmed_schedule()
        assert len(confirmed.confirmation_requests) >= 1

        cancelled = _make_cancelled_schedule()
        assert len(cancelled.confirmation_requests) >= 1

    def test_multiple_operations_maintain_invariants(self) -> None:
        """Exercise a complex flow.

        create -> confirm -> reschedule -> reject -> reschedule -> confirm.
        """
        org = UserId.generate()
        cp = UserId.generate()
        schedule = Schedule.create(
            organizer_id=org,
            counterpart_id=cp,
            scheduled_at=_FUTURE,
            requested_by=org,
            now=_NOW,
        )

        # Counterpart confirms creation
        t0 = datetime(2026, 3, 20, 10, 30)
        schedule.confirm(actor_id=cp, now=t0)
        assert schedule.status == ScheduleStatus.CONFIRMED

        # Organizer reschedules
        t1 = datetime(2026, 3, 20, 11, 0)
        schedule.reschedule(actor_id=org, new_proposed_at=_FUTURE2, now=t1)
        assert schedule.status == ScheduleStatus.REQUESTED

        # Counterpart rejects the reschedule (has prior approval -> revert)
        t2 = datetime(2026, 3, 20, 12, 0)
        schedule.reject(actor_id=cp, now=t2)
        assert schedule.status == ScheduleStatus.CONFIRMED

        # Counterpart reschedules
        new_time = datetime(2026, 5, 1, 10, 0)
        t3 = datetime(2026, 3, 20, 13, 0)
        schedule.reschedule(actor_id=cp, new_proposed_at=new_time, now=t3)
        assert schedule.status == ScheduleStatus.REQUESTED

        # Organizer confirms
        t4 = datetime(2026, 3, 20, 14, 0)
        schedule.confirm(actor_id=org, now=t4)
        assert schedule.status == ScheduleStatus.CONFIRMED
        assert schedule.scheduled_at == new_time

        # Verify invariants
        pending_count = sum(
            1
            for r in schedule.confirmation_requests
            if r.resolution == ConfirmationResolution.PENDING
        )
        assert pending_count == 0
        assert len(schedule.confirmation_requests) == 3
