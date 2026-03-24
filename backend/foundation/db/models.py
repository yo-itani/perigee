"""Aggregation module for all ORM table definitions.

Import all table models here so that Alembic's autogenerate can detect them
via Base.metadata. When adding a new table, add an explicit import below.
"""

from contexts.preparation.infrastructure.tables import (
    ConfirmationRequestTable,  # noqa: F401
    ScheduleGroupAgendaTemplateTable,  # noqa: F401
    ScheduleGroupTable,  # noqa: F401
    ScheduleTable,  # noqa: F401
    TemplateAgendaTemplateTable,  # noqa: F401
    TemplateDefaultCounterpartTable,  # noqa: F401
    TemplateTable,  # noqa: F401
)
from contexts.record.infrastructure.tables import (
    ActionItemTable,  # noqa: F401
    CommentTable,  # noqa: F401
    RecordConfirmedAgendaTable,  # noqa: F401
    RecordTable,  # noqa: F401
    RecordViewerTable,  # noqa: F401
)
from contexts.workspace.infrastructure.tables import (
    MembershipTable,  # noqa: F401
    WorkspaceTable,  # noqa: F401
)
from shared.infrastructure.tables import UserTable  # noqa: F401

__all__ = [
    "ActionItemTable",
    "CommentTable",
    "ConfirmationRequestTable",
    "MembershipTable",
    "RecordConfirmedAgendaTable",
    "RecordTable",
    "RecordViewerTable",
    "ScheduleGroupAgendaTemplateTable",
    "ScheduleGroupTable",
    "ScheduleTable",
    "TemplateAgendaTemplateTable",
    "TemplateDefaultCounterpartTable",
    "TemplateTable",
    "UserTable",
    "WorkspaceTable",
]
