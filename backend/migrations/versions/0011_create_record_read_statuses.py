"""create record_read_statuses table

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "record_read_statuses",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("record_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("last_viewed_at", DATETIME(fsp=6), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["records.id"],
            name="fk_record_read_statuses_record_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_record_read_statuses_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "record_id",
            "user_id",
            name="uq_record_read_statuses_record_id_user_id",
        ),
    )
    op.create_index(
        "idx_record_read_statuses_user_id",
        "record_read_statuses",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_record_read_statuses_user_id",
        table_name="record_read_statuses",
    )
    op.drop_table("record_read_statuses")
