"""In-memory implementation of LoginAttemptRepository for testing."""

from __future__ import annotations

from datetime import datetime

from foundation.auth.login_attempt_repository import (
    LoginAttemptRecord,
    LoginAttemptRepository,
)


class InMemoryLoginAttemptRepository(LoginAttemptRepository):
    """In-memory stub for LoginAttemptRepository."""

    def __init__(self) -> None:
        self._records: list[LoginAttemptRecord] = []

    async def save(self, record: LoginAttemptRecord) -> None:
        self._records.append(record)

    async def count_recent_failures(self, email: str, since: datetime) -> int:
        return sum(
            1
            for r in self._records
            if r.email == email and not r.is_success and r.attempted_at >= since
        )

    async def delete_older_than(self, before: datetime) -> int:
        original_len = len(self._records)
        self._records = [r for r in self._records if r.attempted_at >= before]
        return original_len - len(self._records)
