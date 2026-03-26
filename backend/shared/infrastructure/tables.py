from sqlalchemy import CHAR, Boolean, String
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
