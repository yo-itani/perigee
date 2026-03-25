from __future__ import annotations

from abc import abstractmethod

from contexts.record.domain.comment import Comment
from contexts.record.domain.value_objects import CommentId, RecordId
from foundation.domain.base_repository import BaseRepository


class CommentRepository(BaseRepository[Comment, CommentId]):
    """Repository interface for Comment aggregates.

    Comment is insert-only: save() must raise an exception
    if the entity already exists.
    """

    @abstractmethod
    async def list_by_record_id(self, record_id: RecordId) -> list[Comment]:
        """Return all comments for a given Record.

        Results are ordered by created_at ascending (oldest first).
        """
