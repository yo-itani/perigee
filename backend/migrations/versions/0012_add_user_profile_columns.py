"""add user profile columns (name, email, role, is_active, slack_user_id)

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns as nullable first for backfill
    op.add_column("users", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.add_column("users", sa.Column("slack_user_id", sa.String(255), nullable=True))

    # Backfill existing rows
    op.execute(
        sa.text(
            "UPDATE users SET "
            "name = 'Unknown', "
            "email = CONCAT(id, '@placeholder.local'), "
            "role = 'admin', "
            "is_active = TRUE "
            "WHERE name IS NULL"
        )
    )

    # Make columns non-nullable after backfill
    op.alter_column("users", "name", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "role", existing_type=sa.String(20), nullable=False)
    op.alter_column("users", "is_active", existing_type=sa.Boolean(), nullable=False)

    # Add unique constraint on email
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "slack_user_id")
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
    op.drop_column("users", "email")
    op.drop_column("users", "name")
