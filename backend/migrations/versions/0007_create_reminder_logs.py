"""create reminder_logs table

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("schedule_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("scheduled_at", sa.DATETIME(), nullable=False),
        sa.Column("sent_at", sa.DATETIME(), nullable=False),
        sa.Column("reminder_minutes_before", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "schedule_id",
            "user_id",
            "scheduled_at",
            name="uq_reminder_logs_schedule_user_scheduled_at",
        ),
    )


def downgrade() -> None:
    op.drop_table("reminder_logs")
