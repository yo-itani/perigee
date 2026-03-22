from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.preparation.domain.confirmation_request import ConfirmationRequest
from contexts.preparation.domain.events import (
    ScheduleCancelled,
    ScheduleConfirmed,
    ScheduleCreated,
    ScheduleRejected,
    ScheduleRenamed,
    ScheduleRescheduled,
)
from contexts.preparation.domain.exceptions import (
    InvalidScheduleOperationError,
    NoPendingConfirmationRequestError,
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import (
    ConfirmationRequestType,
    ConfirmationResolution,
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
)
from shared.domain.value_objects import UserId

type _ScheduleEvent = (
    ScheduleCreated
    | ScheduleConfirmed
    | ScheduleRejected
    | ScheduleRescheduled
    | ScheduleCancelled
    | ScheduleRenamed
)


@dataclass
class Schedule:
    """Aggregate root: a 1-on-1 meeting schedule.

    Business rules:
    - Organizer and counterpart must be different users.
    - Schedule cannot be created in the past.
    - Confirm/reject requires a pending confirmation request and must be
      done by the counterpart of the request (not the requester).
    - Cancelled schedules cannot be modified.
    - Reschedule creates a new confirmation request; existing pending
      requests are resolved (superseded or rejected depending on actor).
    - Auto-confirm is a system operation that skips permission checks.
    """

    id: ScheduleId
    organizer_id: UserId
    counterpart_id: UserId
    schedule_group_id: ScheduleGroupId | None
    _title: ScheduleTitle
    _scheduled_at: datetime
    _status: ScheduleStatus
    _confirmation_requests: list[ConfirmationRequest]
    created_at: datetime
    _updated_at: datetime
    _events: list[_ScheduleEvent] = field(default_factory=list, repr=False)

    @property
    def title(self) -> ScheduleTitle:
        return self._title

    @property
    def scheduled_at(self) -> datetime:
        return self._scheduled_at

    @property
    def status(self) -> ScheduleStatus:
        return self._status

    @property
    def confirmation_requests(self) -> list[ConfirmationRequest]:
        return list(self._confirmation_requests)

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def collect_events(self) -> list[_ScheduleEvent]:
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
        counterpart_id: UserId,
        scheduled_at: datetime,
        requested_by: UserId,
        title: str,
        schedule_group_id: ScheduleGroupId | None = None,
        now: datetime | None = None,
    ) -> Schedule:
        """Create a new schedule in Requested status.

        Args:
            organizer_id: The organizer of the 1-on-1.
            counterpart_id: The counterpart of the 1-on-1.
            scheduled_at: Proposed datetime for the meeting.
            requested_by: The user creating the schedule (must be
                organizer or counterpart).
            title: The title of the schedule.
            schedule_group_id: Optional group ID if created via
                ScheduleGroup.
            now: Current time (defaults to UTC now).

        Raises:
            InvalidScheduleOperationError: If organizer == counterpart
                or scheduled_at is in the past.
            UnauthorizedScheduleOperationError: If requested_by is
                neither the organizer nor the counterpart.
            InvalidScheduleTitleError: If title fails validation.
        """
        ts = now or datetime.now(UTC)

        if organizer_id == counterpart_id:
            raise InvalidScheduleOperationError(
                "Organizer and counterpart must be different users."
            )

        # Compare at second precision in UTC
        if _truncate_to_seconds(scheduled_at) < _truncate_to_seconds(ts):
            raise InvalidScheduleOperationError("Cannot create a schedule in the past.")

        if requested_by != organizer_id and requested_by != counterpart_id:
            raise UnauthorizedScheduleOperationError(
                "Only the organizer or counterpart can create a schedule."
            )

        schedule_title = ScheduleTitle(title)
        schedule_id = ScheduleId.generate()
        creation_request = ConfirmationRequest.create(
            request_type=ConfirmationRequestType.CREATION,
            requested_by=requested_by,
            proposed_at=scheduled_at,
            now=ts,
        )

        schedule = Schedule(
            id=schedule_id,
            organizer_id=organizer_id,
            counterpart_id=counterpart_id,
            schedule_group_id=schedule_group_id,
            _title=schedule_title,
            _scheduled_at=scheduled_at,
            _status=ScheduleStatus.REQUESTED,
            _confirmation_requests=[creation_request],
            created_at=ts,
            _updated_at=ts,
        )
        schedule._events.append(
            ScheduleCreated(
                schedule_id=schedule_id,
                organizer_id=organizer_id,
                counterpart_id=counterpart_id,
                scheduled_at=scheduled_at,
                requested_by=requested_by,
                occurred_at=ts,
            )
        )
        return schedule

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def confirm(self, *, actor_id: UserId, now: datetime) -> None:
        """Confirm the pending confirmation request.

        Check order: Cancelled -> Pending existence -> Permission.

        Raises:
            ScheduleAlreadyCancelledError: If already cancelled.
            NoPendingConfirmationRequestError: If no pending request.
            UnauthorizedScheduleOperationError: If actor is the requester
                or not a participant.
        """
        self._assert_not_cancelled()
        pending = self._get_pending_request()
        self._assert_participant(actor_id)
        self._assert_not_requester(actor_id, pending)

        pending.approve(resolved_by=actor_id)
        self._scheduled_at = pending.proposed_at
        self._status = ScheduleStatus.CONFIRMED
        self._updated_at = now
        self._events.append(
            ScheduleConfirmed(
                schedule_id=self.id,
                organizer_id=self.organizer_id,
                counterpart_id=self.counterpart_id,
                scheduled_at=self._scheduled_at,
                confirmed_by=actor_id,
                is_auto=False,
                occurred_at=now,
            )
        )

    def reject(self, *, actor_id: UserId, now: datetime) -> None:
        """Reject the pending confirmation request.

        Check order: Cancelled -> Pending existence -> Permission.

        If the pending request is a Creation type, rejecting it cancels
        the schedule entirely (ScheduleCancelled event, not ScheduleRejected).
        If it is a Reschedule type:
        - If previously confirmed (approved request exists), reverts to Confirmed.
        - If never confirmed, cancels the schedule (ScheduleCancelled event).

        Raises:
            ScheduleAlreadyCancelledError: If already cancelled.
            NoPendingConfirmationRequestError: If no pending request.
            UnauthorizedScheduleOperationError: If actor is the requester
                or not a participant.
        """
        self._assert_not_cancelled()
        pending = self._get_pending_request()
        self._assert_participant(actor_id)
        self._assert_not_requester(actor_id, pending)

        pending.reject(resolved_by=actor_id)
        self._updated_at = now

        if pending.request_type == ConfirmationRequestType.CREATION:
            # Rejecting creation = cancellation
            self._status = ScheduleStatus.CANCELLED
            self._events.append(
                ScheduleCancelled(
                    schedule_id=self.id,
                    organizer_id=self.organizer_id,
                    counterpart_id=self.counterpart_id,
                    cancelled_by=actor_id,
                    occurred_at=now,
                )
            )
        elif self._has_approved_request():
            # Rejecting reschedule when previously confirmed = revert to Confirmed
            self._status = ScheduleStatus.CONFIRMED
            self._events.append(
                ScheduleRejected(
                    schedule_id=self.id,
                    organizer_id=self.organizer_id,
                    counterpart_id=self.counterpart_id,
                    rejected_by=actor_id,
                    occurred_at=now,
                )
            )
        else:
            # Rejecting reschedule when never confirmed = cancellation
            self._status = ScheduleStatus.CANCELLED
            self._events.append(
                ScheduleCancelled(
                    schedule_id=self.id,
                    organizer_id=self.organizer_id,
                    counterpart_id=self.counterpart_id,
                    cancelled_by=actor_id,
                    occurred_at=now,
                )
            )

    def reschedule(
        self,
        *,
        actor_id: UserId,
        new_proposed_at: datetime,
        now: datetime,
    ) -> None:
        """Propose a reschedule.

        If there is an existing pending request:
        - If actor is the same as pending requester -> Superseded
        - If actor is the counterpart of pending requester -> Rejected

        Raises:
            ScheduleAlreadyCancelledError: If already cancelled.
            UnauthorizedScheduleOperationError: If actor is not a participant.
        """
        self._assert_not_cancelled()
        self._assert_participant(actor_id)

        # Resolve existing pending request if any
        existing_pending = self._find_pending_request()
        if existing_pending is not None:
            if existing_pending.requested_by == actor_id:
                existing_pending.supersede()
            else:
                existing_pending.reject(resolved_by=actor_id)

        new_request = ConfirmationRequest.create(
            request_type=ConfirmationRequestType.RESCHEDULE,
            requested_by=actor_id,
            proposed_at=new_proposed_at,
            now=now,
        )
        self._confirmation_requests.append(new_request)
        self._status = ScheduleStatus.REQUESTED
        self._updated_at = now
        self._events.append(
            ScheduleRescheduled(
                schedule_id=self.id,
                organizer_id=self.organizer_id,
                counterpart_id=self.counterpart_id,
                new_proposed_at=new_proposed_at,
                requested_by=actor_id,
                occurred_at=now,
            )
        )

    def cancel(self, *, actor_id: UserId, now: datetime) -> None:
        """Cancel the schedule.

        Raises:
            ScheduleAlreadyCancelledError: If already cancelled.
            UnauthorizedScheduleOperationError: If actor is not a participant.
        """
        self._assert_not_cancelled()
        self._assert_participant(actor_id)

        # Resolve any pending request
        existing_pending = self._find_pending_request()
        if existing_pending is not None:
            existing_pending.supersede()

        self._status = ScheduleStatus.CANCELLED
        self._updated_at = now
        self._events.append(
            ScheduleCancelled(
                schedule_id=self.id,
                organizer_id=self.organizer_id,
                counterpart_id=self.counterpart_id,
                cancelled_by=actor_id,
                occurred_at=now,
            )
        )

    def auto_confirm(self, *, now: datetime) -> None:
        """Auto-confirm triggered by record creation.

        System operation: no actor, no permission check.
        - Requested: confirm the pending request.
        - Confirmed: idempotent (no-op).
        - Cancelled: error.

        Raises:
            ScheduleAlreadyCancelledError: If cancelled.
        """
        self._assert_not_cancelled()

        if self._status == ScheduleStatus.CONFIRMED:
            return  # idempotent

        pending = self._get_pending_request()
        pending.approve(resolved_by=None)
        self._scheduled_at = pending.proposed_at
        self._status = ScheduleStatus.CONFIRMED
        self._updated_at = now
        self._events.append(
            ScheduleConfirmed(
                schedule_id=self.id,
                organizer_id=self.organizer_id,
                counterpart_id=self.counterpart_id,
                scheduled_at=self._scheduled_at,
                confirmed_by=None,
                is_auto=True,
                occurred_at=now,
            )
        )

    def rename(self, *, new_title: str, now: datetime) -> None:
        """Rename the schedule.

        No-op if the new title is the same as the current title
        (after normalization).

        Cancelled schedules can also be renamed. This is intentional
        because ScheduleGroup.rename propagates to all child schedules
        regardless of their status.

        Args:
            new_title: The new title for the schedule.
            now: Current time.

        Raises:
            InvalidScheduleTitleError: If new_title fails validation.
        """
        title = ScheduleTitle(new_title)
        if title == self._title:
            return
        self._title = title
        self._updated_at = now
        self._events.append(
            ScheduleRenamed(
                schedule_id=self.id,
                new_title=title.value,
                occurred_at=now,
            )
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_not_cancelled(self) -> None:
        if self._status == ScheduleStatus.CANCELLED:
            raise ScheduleAlreadyCancelledError()

    def _assert_participant(self, actor_id: UserId) -> None:
        if actor_id != self.organizer_id and actor_id != self.counterpart_id:
            raise UnauthorizedScheduleOperationError(
                "Only the organizer or counterpart can operate on this schedule."
            )

    def _assert_not_requester(
        self, actor_id: UserId, pending: ConfirmationRequest
    ) -> None:
        if actor_id == pending.requested_by:
            raise UnauthorizedScheduleOperationError(
                "Cannot confirm or reject your own request."
            )

    def _has_approved_request(self) -> bool:
        """Check whether any confirmation request has been approved."""
        return any(
            req.resolution == ConfirmationResolution.APPROVED
            for req in self._confirmation_requests
        )

    def _find_pending_request(self) -> ConfirmationRequest | None:
        """Find the pending confirmation request (if any)."""
        for req in reversed(self._confirmation_requests):
            if req.resolution == ConfirmationResolution.PENDING:
                return req
        return None

    def _get_pending_request(self) -> ConfirmationRequest:
        """Get the pending confirmation request or raise."""
        pending = self._find_pending_request()
        if pending is None:
            raise NoPendingConfirmationRequestError()
        return pending


def _truncate_to_seconds(dt: datetime) -> datetime:
    """Truncate datetime to second precision for comparison."""
    return dt.replace(microsecond=0)
