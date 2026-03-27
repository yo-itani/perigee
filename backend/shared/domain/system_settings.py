"""SystemSettings entity for managing system-wide configuration."""

from __future__ import annotations

from datetime import datetime


class SystemSettings:
    """Singleton entity representing system-wide settings.

    Always exists as exactly one row (id=1) in the database.
    Used primarily for exclusive control of the first-user setup flow.
    """

    def __init__(
        self,
        setup_completed_at: datetime | None = None,
    ) -> None:
        self._setup_completed_at = setup_completed_at

    @property
    def setup_completed_at(self) -> datetime | None:
        return self._setup_completed_at

    @property
    def is_setup_complete(self) -> bool:
        return self._setup_completed_at is not None

    def mark_setup_complete(self, now: datetime) -> None:
        """Mark the initial setup as complete."""
        self._setup_completed_at = now
