from __future__ import annotations

from abc import abstractmethod

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.value_objects import ReadStatusId, RecordId
from foundation.domain.base_repository import BaseRepository
from shared.domain.value_objects import UserId


class ReadStatusRepository(BaseRepository[ReadStatus, ReadStatusId]):
    """Repository interface for ReadStatus entities."""

    # get_by_id + save inherited from BaseRepository

    @abstractmethod
    async def find_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> ReadStatus | None:
        """Find the ReadStatus for a specific Record and user combination."""

    @abstractmethod
    async def upsert(self, entity: ReadStatus) -> None:
        """Insert or update a ReadStatus by (record_id, user_id).

        If a row with the same (record_id, user_id) already exists,
        update last_viewed_at. Otherwise insert a new row.
        This is safe against concurrent requests.
        """

    @abstractmethod
    async def delete_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> None:
        """Delete the ReadStatus for a specific Record and user.

        Used when a Viewer is removed from a Record.
        No-op if no matching ReadStatus exists.
        """
