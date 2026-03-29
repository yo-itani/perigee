"""update all TimestampMixin created_at/updated_at columns to DATETIME(6)

Revision ID: 0016
Revises: 0015
Create Date: 2026-03-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# All tables that use TimestampMixin (created_at + updated_at).
_TABLES_WITH_TIMESTAMP_MIXIN: list[str] = [
    "users",
    "system_settings",
    "templates",
    "template_default_counterparts",
    "template_agenda_templates",
    "schedule_groups",
    "schedule_group_agenda_templates",
    "schedules",
    "confirmation_requests",
    "agendas",
    "agenda_comments",
    "records",
    "record_viewers",
    "record_confirmed_agendas",
    "comments",
    "action_items",
    "record_read_statuses",
    "notification_settings",
    "reminder_logs",
    "notification_records",
    "workspaces",
    "memberships",
]


def upgrade() -> None:
    for table in _TABLES_WITH_TIMESTAMP_MIXIN:
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(),
            type_=DATETIME(fsp=6),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        )
        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(),
            type_=DATETIME(fsp=6),
            existing_nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            ),
        )


def downgrade() -> None:
    for table in reversed(_TABLES_WITH_TIMESTAMP_MIXIN):
        op.alter_column(
            table,
            "updated_at",
            existing_type=DATETIME(fsp=6),
            type_=sa.DateTime(),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        )
        op.alter_column(
            table,
            "created_at",
            existing_type=DATETIME(fsp=6),
            type_=sa.DateTime(),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
