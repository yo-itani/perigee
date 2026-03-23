"""create record tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "records",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("organizer_id", sa.CHAR(36), nullable=False),
        sa.Column("counterpart_id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_id", sa.CHAR(36), nullable=True),
        sa.Column("memo", sa.TEXT(), nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False),
        sa.Column(
            "conducted_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
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
            name="fk_records_organizer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counterpart_id"],
            ["users.id"],
            name="fk_records_counterpart_id",
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "record_viewers",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("record_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
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
            ["record_id"],
            ["records.id"],
            name="fk_record_viewers_record_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_record_viewers_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "record_id", "user_id", name="uq_record_viewers_record_id_user_id"
        ),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("record_id", sa.CHAR(36), nullable=False),
        sa.Column("author_id", sa.CHAR(36), nullable=False),
        sa.Column("body", sa.TEXT(), nullable=False),
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
            ["record_id"],
            ["records.id"],
            name="fk_comments_record_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_comments_author_id",
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "action_items",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("counterpart_id", sa.CHAR(36), nullable=False),
        sa.Column("record_id", sa.CHAR(36), nullable=False),
        sa.Column("title", sa.VARCHAR(200), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="0"),
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
            ["counterpart_id"],
            ["users.id"],
            name="fk_action_items_counterpart_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["records.id"],
            name="fk_action_items_record_id",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("action_items")
    op.drop_table("comments")
    op.drop_table("record_viewers")
    op.drop_table("records")
