from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.preparation.domain.value_objects import (
    ConfirmationRequestId,
    ConfirmationRequestType,
    ConfirmationResolution,
)
from shared.domain.value_objects import UserId


@dataclass
class ConfirmationRequest:
    """Child entity of Schedule representing an approval request.

    Created when a schedule is first created (Creation type) or when
    a reschedule is proposed (Reschedule type). Tracks the resolution
    lifecycle: Pending -> Approved/Rejected/Superseded.
    """

    id: ConfirmationRequestId
    request_type: ConfirmationRequestType
    requested_by: UserId
    proposed_at: datetime
    _resolution: ConfirmationResolution
    _resolved_by: UserId | None
    created_at: datetime

    @property
    def resolution(self) -> ConfirmationResolution:
        return self._resolution

    @property
    def resolved_by(self) -> UserId | None:
        return self._resolved_by

    @property
    def is_pending(self) -> bool:
        return self._resolution == ConfirmationResolution.PENDING

    def approve(self, resolved_by: UserId | None) -> None:
        """Mark this request as approved."""
        self._resolution = ConfirmationResolution.APPROVED
        self._resolved_by = resolved_by

    def reject(self, resolved_by: UserId) -> None:
        """Mark this request as rejected."""
        self._resolution = ConfirmationResolution.REJECTED
        self._resolved_by = resolved_by

    def supersede(self) -> None:
        """Mark this request as superseded by a newer request."""
        self._resolution = ConfirmationResolution.SUPERSEDED

    @staticmethod
    def create(
        *,
        request_type: ConfirmationRequestType,
        requested_by: UserId,
        proposed_at: datetime,
        now: datetime,
    ) -> ConfirmationRequest:
        """Factory method to create a new pending confirmation request."""
        return ConfirmationRequest(
            id=ConfirmationRequestId.generate(),
            request_type=request_type,
            requested_by=requested_by,
            proposed_at=proposed_at,
            _resolution=ConfirmationResolution.PENDING,
            _resolved_by=None,
            created_at=now,
        )
