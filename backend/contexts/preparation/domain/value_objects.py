from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ScheduleId:
    """Schedule identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> ScheduleId:
        return ScheduleId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ScheduleId:
        return ScheduleId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class ConfirmationRequestId:
    """ConfirmationRequest identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> ConfirmationRequestId:
        return ConfirmationRequestId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ConfirmationRequestId:
        return ConfirmationRequestId(value=uuid.UUID(raw))


class ScheduleStatus(Enum):
    """Schedule status: Requested -> Confirmed -> Cancelled."""

    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ConfirmationRequestType(Enum):
    """Type of confirmation request."""

    CREATION = "creation"
    RESCHEDULE = "reschedule"


class ConfirmationResolution(Enum):
    """Resolution of a confirmation request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
