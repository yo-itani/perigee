from __future__ import annotations

from contexts.record.domain.comment import Comment
from contexts.record.domain.value_objects import CommentId
from foundation.domain.base_repository import BaseRepository


class CommentRepository(BaseRepository[Comment, CommentId]):
    """Repository interface for Comment aggregates.

    Comment is insert-only: save() must raise an exception
    if the entity already exists.
    """

    pass
