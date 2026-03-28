"""create refresh_tokens, invitation_tokens, and login_attempts tables

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("token_family_id", sa.CHAR(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_refresh_tokens_user_id_is_revoked",
        "refresh_tokens",
        ["user_id", "is_revoked"],
    )
    op.create_index(
        "ix_refresh_tokens_family_is_revoked",
        "refresh_tokens",
        ["token_family_id", "is_revoked"],
    )
    op.create_index(
        "ix_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
    )

    # --- invitation_tokens ---
    op.create_table(
        "invitation_tokens",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_used", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_invitation_tokens_token_hash",
        "invitation_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_invitation_tokens_user_id_is_used",
        "invitation_tokens",
        ["user_id", "is_used"],
    )

    # --- login_attempts ---
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("is_success", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_login_attempts_email_attempted_at",
        "login_attempts",
        ["email", "attempted_at"],
    )
    op.create_index(
        "ix_login_attempts_ip_attempted_at",
        "login_attempts",
        ["ip_address", "attempted_at"],
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("invitation_tokens")
    op.drop_table("refresh_tokens")
