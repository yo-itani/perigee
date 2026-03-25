from datetime import datetime

from sqlalchemy import (
    CHAR,
    INTEGER,
    TEXT,
    VARCHAR,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from foundation.db.base import Base, TimestampMixin

# ------------------------------------------------------------------
# Template
# ------------------------------------------------------------------


class TemplateTable(Base, TimestampMixin):
    """ORM model for the templates table."""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", name="fk_templates_organizer_id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)

    default_counterparts: Mapped[list["TemplateDefaultCounterpartTable"]] = (
        relationship(
            back_populates="template",
            lazy="selectin",
            cascade="all, delete-orphan",
        )
    )
    agenda_templates: Mapped[list["TemplateAgendaTemplateTable"]] = relationship(
        back_populates="template",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TemplateDefaultCounterpartTable(Base, TimestampMixin):
    """ORM model for the template_default_counterparts table."""

    __tablename__ = "template_default_counterparts"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "user_id",
            name="uq_template_default_counterparts_template_user",
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "templates.id",
            name="fk_template_default_counterparts_template_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_template_default_counterparts_user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(INTEGER, nullable=False)

    template: Mapped["TemplateTable"] = relationship(
        back_populates="default_counterparts",
    )


class TemplateAgendaTemplateTable(Base, TimestampMixin):
    """ORM model for the template_agenda_templates table."""

    __tablename__ = "template_agenda_templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "templates.id",
            name="fk_template_agenda_templates_template_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(VARCHAR(200), nullable=False)
    position: Mapped[int] = mapped_column(INTEGER, nullable=False)

    template: Mapped["TemplateTable"] = relationship(
        back_populates="agenda_templates",
    )


# ------------------------------------------------------------------
# ScheduleGroup
# ------------------------------------------------------------------


class ScheduleGroupTable(Base, TimestampMixin):
    """ORM model for the schedule_groups table."""

    __tablename__ = "schedule_groups"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_schedule_groups_organizer_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    template_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey(
            "templates.id",
            name="fk_schedule_groups_template_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)

    agenda_templates: Mapped[list["ScheduleGroupAgendaTemplateTable"]] = relationship(
        back_populates="schedule_group",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ScheduleGroupAgendaTemplateTable(Base, TimestampMixin):
    """ORM model for the schedule_group_agenda_templates table."""

    __tablename__ = "schedule_group_agenda_templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    schedule_group_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "schedule_groups.id",
            name="fk_schedule_group_agenda_templates_schedule_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(VARCHAR(200), nullable=False)
    position: Mapped[int] = mapped_column(INTEGER, nullable=False)

    schedule_group: Mapped["ScheduleGroupTable"] = relationship(
        back_populates="agenda_templates",
    )


# ------------------------------------------------------------------
# Schedule
# ------------------------------------------------------------------


class ScheduleTable(Base, TimestampMixin):
    """ORM model for the schedules table."""

    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_schedules_organizer_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    counterpart_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_schedules_counterpart_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    schedule_group_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey(
            "schedule_groups.id",
            name="fk_schedules_schedule_group_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    confirmation_requests: Mapped[list["ConfirmationRequestTable"]] = relationship(
        back_populates="schedule",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ConfirmationRequestTable(Base, TimestampMixin):
    """ORM model for the confirmation_requests table."""

    __tablename__ = "confirmation_requests"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "schedules.id",
            name="fk_confirmation_requests_schedule_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    requested_by: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_confirmation_requests_requested_by",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    proposed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    resolution: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_confirmation_requests_resolved_by",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    schedule: Mapped["ScheduleTable"] = relationship(
        back_populates="confirmation_requests",
    )


# ------------------------------------------------------------------
# Agenda
# ------------------------------------------------------------------


class AgendaTable(Base, TimestampMixin):
    """ORM model for the agendas table."""

    __tablename__ = "agendas"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "schedules.id",
            name="fk_agendas_schedule_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(VARCHAR(200), nullable=False)
    added_by: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_agendas_added_by",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    added_by_tag: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    comments: Mapped[list["AgendaCommentTable"]] = relationship(
        back_populates="agenda",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class AgendaCommentTable(Base, TimestampMixin):
    """ORM model for the agenda_comments table."""

    __tablename__ = "agenda_comments"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    agenda_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "agendas.id",
            name="fk_agenda_comments_agenda_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    author_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey(
            "users.id",
            name="fk_agenda_comments_author_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(TEXT, nullable=False)

    agenda: Mapped["AgendaTable"] = relationship(
        back_populates="comments",
    )
