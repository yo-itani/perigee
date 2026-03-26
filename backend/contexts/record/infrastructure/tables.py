from datetime import datetime

from sqlalchemy import CHAR, TEXT, VARCHAR, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from foundation.db.base import Base, TimestampMixin


class RecordTable(Base, TimestampMixin):
    """ORM model for the records table."""

    __tablename__ = "records"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_records_organizer_id"),
        nullable=False,
    )
    counterpart_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_records_counterpart_id"),
        nullable=False,
    )
    schedule_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    memo: Mapped[str] = mapped_column(TEXT, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    conducted_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    latest_activity_at: Mapped[datetime | None] = mapped_column(
        DATETIME(fsp=6), nullable=True
    )

    viewers: Mapped[list["RecordViewerTable"]] = relationship(
        back_populates="record",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    confirmed_agendas: Mapped[list["RecordConfirmedAgendaTable"]] = relationship(
        back_populates="record",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class RecordViewerTable(Base, TimestampMixin):
    """ORM model for the record_viewers table."""

    __tablename__ = "record_viewers"
    __table_args__ = (
        UniqueConstraint(
            "record_id", "user_id", name="uq_record_viewers_record_id_user_id"
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    record_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "records.id", ondelete="CASCADE", name="fk_record_viewers_record_id"
        ),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_record_viewers_user_id"),
        nullable=False,
    )

    record: Mapped["RecordTable"] = relationship(back_populates="viewers")


class RecordConfirmedAgendaTable(Base, TimestampMixin):
    """ORM model for the record_confirmed_agendas table."""

    __tablename__ = "record_confirmed_agendas"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "agenda_id",
            name="uq_record_confirmed_agendas_record_id_agenda_id",
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    record_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "records.id",
            ondelete="CASCADE",
            name="fk_record_confirmed_agendas_record_id",
        ),
        nullable=False,
    )
    agenda_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)

    record: Mapped["RecordTable"] = relationship(back_populates="confirmed_agendas")


class CommentTable(Base, TimestampMixin):
    """ORM model for the comments table."""

    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    record_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("records.id", ondelete="CASCADE", name="fk_comments_record_id"),
        nullable=False,
    )
    author_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_comments_author_id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(TEXT, nullable=False)


class ActionItemTable(Base, TimestampMixin):
    """ORM model for the action_items table."""

    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    counterpart_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id", ondelete="RESTRICT", name="fk_action_items_counterpart_id"
        ),
        nullable=False,
    )
    record_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("records.id", ondelete="CASCADE", name="fk_action_items_record_id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(VARCHAR(200), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ReadStatusTable(Base, TimestampMixin):
    """ORM model for the record_read_statuses table."""

    __tablename__ = "record_read_statuses"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "user_id",
            name="uq_record_read_statuses_record_id_user_id",
        ),
        Index("idx_record_read_statuses_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    record_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "records.id",
            ondelete="CASCADE",
            name="fk_record_read_statuses_record_id",
        ),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_record_read_statuses_user_id",
        ),
        nullable=False,
    )
    last_viewed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
