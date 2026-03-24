from sqlalchemy import CHAR, Boolean, Integer
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
