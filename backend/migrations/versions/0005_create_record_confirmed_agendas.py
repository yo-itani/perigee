"""create record_confirmed_agendas table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "record_confirmed_agendas",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("record_id", sa.CHAR(36), nullable=False),
        sa.Column("agenda_id", sa.CHAR(36), nullable=False),
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
            name="fk_record_confirmed_agendas_record_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "record_id",
            "agenda_id",
            name="uq_record_confirmed_agendas_record_id_agenda_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("record_confirmed_agendas")
