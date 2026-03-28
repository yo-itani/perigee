"""Polyfactory-based test data factories.

Provides deterministic, customizable builders for ORM table rows
and domain entities used across integration and unit tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from polyfactory.factories import DataclassFactory

from shared.domain.value_objects import UserId
from shared.infrastructure.tables import SystemSettingsTable, UserTable


class UserTableFactory:
    """Factory for creating UserTable rows with sensible defaults.

    polyfactory does not natively support SQLAlchemy ORM models, so we
    use a thin wrapper that delegates to the constructor directly.
    """

    @staticmethod
    def build(
        *,
        id: str | None = None,
        name: str = "Test User",
        email: str | None = None,
        role: str = "member",
        is_active: bool = True,
        slack_user_id: str | None = None,
        password_hash: str | None = None,
    ) -> UserTable:
        uid = id or str(uuid.uuid4())
        return UserTable(
            id=uid,
            name=name,
            email=email or f"{uid}@test.local",
            role=role,
            is_active=is_active,
            slack_user_id=slack_user_id,
            password_hash=password_hash,
        )


class SystemSettingsTableFactory:
    """Factory for creating SystemSettingsTable rows."""

    @staticmethod
    def build(
        *,
        id: int = 1,
        setup_completed_at: datetime | None = None,
    ) -> SystemSettingsTable:
        return SystemSettingsTable(
            id=id,
            setup_completed_at=setup_completed_at,
        )

    @staticmethod
    def build_completed() -> SystemSettingsTable:
        """Build a SystemSettingsTable with setup already completed."""
        return SystemSettingsTable(
            id=1,
            setup_completed_at=datetime.now(UTC),
        )


class UserIdFactory(DataclassFactory[UserId]):
    """Factory for generating UserId value objects."""

    __model__ = UserId
