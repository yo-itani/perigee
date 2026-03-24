from __future__ import annotations

from abc import abstractmethod

from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class RecordRepository(BaseRepository[Record, RecordId]):
    """Repository interface for Record aggregates."""

    # get_by_id + save inherited from BaseRepository

    @abstractmethod
    async def exists_by_participant(
        self, user_id: UserId, counterpart_id: UserId
    ) -> bool:
        """Check if user_id has participated in any Record with counterpart_id.

        A participant is either the organizer or the counterpart of a Record
        where counterpart_id is the counterpart.
        """

    @abstractmethod
    async def list_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
        offset: int,
        limit: int,
    ) -> list[Record]:
        """Return published Records for a pair, visible to actor.

        Visibility: actor is organizer, counterpart, or in viewers list.
        Ordered by conducted_at DESC, then created_at DESC.
        """

    @abstractmethod
    async def count_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> int:
        """Count published Records for a pair, visible to actor."""

    @abstractmethod
    async def get_latest_visible_published_by_pair(
        self,
        actor_id: UserId,
        organizer_id: UserId,
        counterpart_id: UserId,
    ) -> Record | None:
        """Return the latest published Record for a pair, visible to actor.

        Latest = highest conducted_at (then created_at as tiebreaker).
        """
