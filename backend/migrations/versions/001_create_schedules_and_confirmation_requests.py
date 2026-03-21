"""create schedules and confirmation_requests tables

Revision ID: 001
Revises:
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organizer_id", sa.String(36), nullable=False, index=True),
        sa.Column("counterpart_id", sa.String(36), nullable=False, index=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("requested", "confirmed", "cancelled", name="schedule_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "confirmation_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("schedules.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "request_type",
            sa.Enum("creation", "reschedule", name="confirmation_request_type"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(36), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "resolution",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "superseded",
                name="confirmation_resolution",
            ),
            nullable=False,
        ),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("confirmation_requests")
    op.drop_table("schedules")
