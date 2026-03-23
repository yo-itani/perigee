"""create workspace tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("name", sa.VARCHAR(100), nullable=False),
        sa.Column("parent_id", sa.CHAR(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["workspaces.id"],
            name="fk_workspaces_parent_id",
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "memberships",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("role", sa.VARCHAR(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_memberships_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memberships_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_memberships_workspace_user"
        ),
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("workspaces")
