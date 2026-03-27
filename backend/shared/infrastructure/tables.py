from datetime import datetime

from sqlalchemy import CHAR, Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from foundation.db.base import Base, TimestampMixin


class UserTable(Base, TimestampMixin):
    """ORM model for the users table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slack_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )


class SystemSettingsTable(Base, TimestampMixin):
    """ORM model for the system_settings table (singleton row, id=1)."""

    __tablename__ = "system_settings"
    __table_args__ = (CheckConstraint("id = 1", name="chk_system_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    setup_completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
