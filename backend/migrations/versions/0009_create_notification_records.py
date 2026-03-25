"""create notification_records table

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_records",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("recipient_id", sa.CHAR(36), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(512), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DATETIME(), nullable=True),
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
    )
    op.create_index(
        "ix_notification_records_recipient_id",
        "notification_records",
        ["recipient_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_records_recipient_id",
        table_name="notification_records",
    )
    op.drop_table("notification_records")
