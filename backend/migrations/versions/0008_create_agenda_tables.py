"""create agendas and agenda_comments tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- agendas ---
    op.create_table(
        "agendas",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_id", sa.CHAR(36), nullable=False),
        sa.Column("topic", sa.VARCHAR(200), nullable=False),
        sa.Column("added_by", sa.CHAR(36), nullable=False),
        sa.Column("added_by_tag", sa.VARCHAR(20), nullable=False),
        sa.Column(
            "created_at",
            MYSQL_DATETIME(fsp=6),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            MYSQL_DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["schedules.id"],
            name="fk_agendas_schedule_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_agendas_added_by",
            ondelete="RESTRICT",
        ),
    )

    # --- agenda_comments ---
    op.create_table(
        "agenda_comments",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("agenda_id", sa.CHAR(36), nullable=False),
        sa.Column("author_id", sa.CHAR(36), nullable=False),
        sa.Column("body", sa.TEXT(), nullable=False),
        sa.Column(
            "created_at",
            MYSQL_DATETIME(fsp=6),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            MYSQL_DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["agenda_id"],
            ["agendas.id"],
            name="fk_agenda_comments_agenda_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_agenda_comments_author_id",
            ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("agenda_comments")
    op.drop_table("agendas")
