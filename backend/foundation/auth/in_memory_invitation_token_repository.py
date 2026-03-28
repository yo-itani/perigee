"""In-memory implementation of InvitationTokenRepository for testing."""

from __future__ import annotations

from foundation.auth.invitation_token_repository import (
    InvitationTokenRecord,
    InvitationTokenRepository,
)


class InMemoryInvitationTokenRepository(InvitationTokenRepository):
    """In-memory stub for InvitationTokenRepository."""

    def __init__(self) -> None:
        self._records: dict[str, InvitationTokenRecord] = {}

    async def save(self, record: InvitationTokenRecord) -> None:
        self._records[record.id] = record

    async def find_by_token_hash(self, token_hash: str) -> InvitationTokenRecord | None:
        for record in self._records.values():
            if record.token_hash == token_hash:
                return record
        return None

    async def mark_as_used(self, token_id: str) -> None:
        if token_id in self._records:
            self._records[token_id].is_used = True
