"""Aggregation module for all ORM table definitions.

Import all table models here so that Alembic's autogenerate can detect them
via Base.metadata. When adding a new table, add an explicit import below.
"""

from contexts.workspace.infrastructure.tables import (
    MembershipTable,  # noqa: F401
    WorkspaceTable,  # noqa: F401
)
from shared.infrastructure.tables import UserTable  # noqa: F401

__all__ = ["MembershipTable", "UserTable", "WorkspaceTable"]
