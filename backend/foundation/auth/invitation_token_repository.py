"""Repository interface for invitation token persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InvitationTokenRecord:
    """Data class representing a stored invitation token."""

    id: str
    token_hash: str
    user_id: str
    expires_at: datetime
    is_used: bool
    created_at: datetime


class InvitationTokenRepository(ABC):
    """Interface for invitation token persistence."""

    @abstractmethod
    async def save(self, record: InvitationTokenRecord) -> None: ...

    @abstractmethod
    async def find_by_token_hash(
        self, token_hash: str
    ) -> InvitationTokenRecord | None: ...

    @abstractmethod
    async def mark_as_used(self, token_id: str) -> None: ...
