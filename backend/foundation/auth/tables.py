"""ORM table definitions for authentication-related tables."""

from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from foundation.db.base import Base


class RefreshTokenTable(Base):
    """ORM model for the refresh_tokens table."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    token_family_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class InvitationTokenTable(Base):
    """ORM model for the invitation_tokens table."""

    __tablename__ = "invitation_tokens"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class LoginAttemptTable(Base):
    """ORM model for the login_attempts table."""

    __tablename__ = "login_attempts"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
