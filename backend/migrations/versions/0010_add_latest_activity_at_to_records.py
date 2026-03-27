"""add latest_activity_at to records

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable column
    op.add_column(
        "records",
        sa.Column("latest_activity_at", mysql.DATETIME(fsp=6), nullable=True),
    )

    # Backfill: set latest_activity_at for published records using updated_at
    op.execute(
        """
        UPDATE records
        SET latest_activity_at = updated_at
        WHERE status = 'published' AND latest_activity_at IS NULL
        """
    )

    # Backfill: override with latest comment created_at if newer
    op.execute(
        """
        UPDATE records r
        SET latest_activity_at = (
            SELECT MAX(c.created_at)
            FROM comments c
            WHERE c.record_id = r.id
        )
        WHERE r.status = 'published'
          AND EXISTS (
            SELECT 1 FROM comments c
            WHERE c.record_id = r.id AND c.created_at > r.latest_activity_at
          )
        """
    )


def downgrade() -> None:
    op.drop_column("records", "latest_activity_at")
