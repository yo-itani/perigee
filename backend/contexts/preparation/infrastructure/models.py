"""SQLAlchemy ORM models for the Preparation context."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from foundation.db.base import Base


class ScheduleRow(Base):
    """ORM model for the schedules table."""

    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    counterpart_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("requested", "confirmed", "cancelled", name="schedule_status"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    confirmation_requests: Mapped[list["ConfirmationRequestRow"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ConfirmationRequestRow.created_at",
    )


class ConfirmationRequestRow(Base):
    """ORM model for the confirmation_requests table."""

    __tablename__ = "confirmation_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schedules.id"), nullable=False, index=True
    )
    request_type: Mapped[str] = mapped_column(
        Enum("creation", "reschedule", name="confirmation_request_type"),
        nullable=False,
    )
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "approved",
            "rejected",
            "superseded",
            name="confirmation_resolution",
        ),
        nullable=False,
    )
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    schedule: Mapped["ScheduleRow"] = relationship(
        back_populates="confirmation_requests",
    )
