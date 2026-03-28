"""Repository interface for refresh token persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefreshTokenRecord:
    """Data class representing a stored refresh token."""

    id: str
    token_hash: str
    user_id: str
    token_family_id: str
    expires_at: datetime
    is_revoked: bool
    created_at: datetime


class RefreshTokenRepository(ABC):
    """Interface for refresh token persistence."""

    @abstractmethod
    async def save(self, record: RefreshTokenRecord) -> None: ...

    @abstractmethod
    async def find_by_token_hash(
        self, token_hash: str
    ) -> RefreshTokenRecord | None: ...

    @abstractmethod
    async def revoke_by_family_id(self, family_id: str) -> None:
        """Revoke all tokens in the given family."""

    @abstractmethod
    async def revoke_by_user_id(self, user_id: str) -> None:
        """Revoke all tokens for the given user."""

    @abstractmethod
    async def delete_expired(self, before: datetime) -> int:
        """Delete expired tokens older than the given timestamp. Returns count."""
