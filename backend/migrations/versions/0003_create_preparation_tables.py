"""create preparation tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- templates ---
    op.create_table(
        "templates",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("organizer_id", sa.CHAR(36), nullable=False),
        sa.Column("name", sa.VARCHAR(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organizer_id"],
            ["users.id"],
            name="fk_templates_organizer_id",
            ondelete="RESTRICT",
        ),
    )

    # --- template_default_counterparts ---
    op.create_table(
        "template_default_counterparts",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("template_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("position", sa.INTEGER(), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name="fk_template_default_counterparts_template_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_template_default_counterparts_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "template_id",
            "user_id",
            name="uq_template_default_counterparts_template_user",
        ),
    )

    # --- template_agenda_templates ---
    op.create_table(
        "template_agenda_templates",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("template_id", sa.CHAR(36), nullable=False),
        sa.Column("topic", sa.VARCHAR(200), nullable=False),
        sa.Column("position", sa.INTEGER(), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name="fk_template_agenda_templates_template_id",
            ondelete="CASCADE",
        ),
    )

    # --- schedule_groups ---
    op.create_table(
        "schedule_groups",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("organizer_id", sa.CHAR(36), nullable=False),
        sa.Column("template_id", sa.CHAR(36), nullable=True),
        sa.Column("title", sa.VARCHAR(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organizer_id"],
            ["users.id"],
            name="fk_schedule_groups_organizer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name="fk_schedule_groups_template_id",
            ondelete="SET NULL",
        ),
    )

    # --- schedule_group_agenda_templates ---
    op.create_table(
        "schedule_group_agenda_templates",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_group_id", sa.CHAR(36), nullable=False),
        sa.Column("topic", sa.VARCHAR(200), nullable=False),
        sa.Column("position", sa.INTEGER(), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["schedule_group_id"],
            ["schedule_groups.id"],
            name="fk_schedule_group_agenda_templates_schedule_group_id",
            ondelete="CASCADE",
        ),
    )

    # --- schedules ---
    op.create_table(
        "schedules",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("organizer_id", sa.CHAR(36), nullable=False),
        sa.Column("counterpart_id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_group_id", sa.CHAR(36), nullable=True),
        sa.Column("title", sa.VARCHAR(100), nullable=False),
        sa.Column("scheduled_at", MYSQL_DATETIME(fsp=6), nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organizer_id"],
            ["users.id"],
            name="fk_schedules_organizer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counterpart_id"],
            ["users.id"],
            name="fk_schedules_counterpart_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_group_id"],
            ["schedule_groups.id"],
            name="fk_schedules_schedule_group_id",
            ondelete="SET NULL",
        ),
    )

    # --- confirmation_requests ---
    op.create_table(
        "confirmation_requests",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_id", sa.CHAR(36), nullable=False),
        sa.Column("request_type", sa.VARCHAR(20), nullable=False),
        sa.Column("requested_by", sa.CHAR(36), nullable=False),
        sa.Column("proposed_at", MYSQL_DATETIME(fsp=6), nullable=False),
        sa.Column("resolution", sa.VARCHAR(20), nullable=False),
        sa.Column("resolved_by", sa.CHAR(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["schedules.id"],
            name="fk_confirmation_requests_schedule_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_confirmation_requests_requested_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_confirmation_requests_resolved_by",
            ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("confirmation_requests")
    op.drop_table("schedules")
    op.drop_table("schedule_group_agenda_templates")
    op.drop_table("schedule_groups")
    op.drop_table("template_agenda_templates")
    op.drop_table("template_default_counterparts")
    op.drop_table("templates")
