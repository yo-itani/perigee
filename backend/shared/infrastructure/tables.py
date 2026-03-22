from sqlalchemy import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from foundation.db.base import Base, TimestampMixin


class UserTable(Base, TimestampMixin):
    """ORM model for the users table (minimal: id only)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
