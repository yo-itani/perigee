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


@dataclass(frozen=True)
class ScheduleGroupId:
    """ScheduleGroup identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> ScheduleGroupId:
        return ScheduleGroupId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ScheduleGroupId:
        return ScheduleGroupId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class AgendaId:
    """Agenda identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> AgendaId:
        return AgendaId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> AgendaId:
        return AgendaId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class TemplateId:
    """Template identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> TemplateId:
        return TemplateId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> TemplateId:
        return TemplateId(value=uuid.UUID(raw))


@dataclass(frozen=True)
class CommentId:
    """Agenda comment identifier (UUID-based value object)."""

    value: uuid.UUID

    @staticmethod
    def generate() -> CommentId:
        return CommentId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> CommentId:
        return CommentId(value=uuid.UUID(raw))
