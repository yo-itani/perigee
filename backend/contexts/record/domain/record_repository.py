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
