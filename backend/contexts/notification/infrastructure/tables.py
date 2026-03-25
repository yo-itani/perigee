from datetime import datetime

from sqlalchemy import CHAR, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from foundation.db.base import Base, TimestampMixin


class NotificationSettingTable(Base, TimestampMixin):
    """ORM model for the notification_settings table."""

    __tablename__ = "notification_settings"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        unique=True,
        nullable=False,
    )
    reminder_minutes_before: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ReminderLogTable(Base, TimestampMixin):
    """ORM model for the reminder_logs table."""

    __tablename__ = "reminder_logs"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "user_id",
            "scheduled_at",
            name="uq_reminder_logs_schedule_user_scheduled_at",
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    user_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    reminder_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False)
