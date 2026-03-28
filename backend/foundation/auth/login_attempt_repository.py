"""Repository interface for login attempt persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LoginAttemptRecord:
    """Data class representing a stored login attempt."""

    id: str
    email: str
    ip_address: str
    attempted_at: datetime
    is_success: bool


class LoginAttemptRepository(ABC):
    """Interface for login attempt persistence."""

    @abstractmethod
    async def save(self, record: LoginAttemptRecord) -> None: ...

    @abstractmethod
    async def count_recent_failures(
        self, email: str, since: datetime
    ) -> int:
        """Count failed login attempts for the given email since the given time."""

    @abstractmethod
    async def delete_older_than(self, before: datetime) -> int:
        """Delete login attempts older than the given timestamp. Returns count."""
