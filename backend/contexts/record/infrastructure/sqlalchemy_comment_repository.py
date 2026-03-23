from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.record.domain.comment import Comment
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.comment_repository import CommentRepository
from contexts.record.domain.exceptions import CommentAlreadyExistsError
from contexts.record.domain.value_objects import CommentId, RecordId
from contexts.record.infrastructure.tables import CommentTable
from shared.domain.value_objects import UserId


class SqlAlchemyCommentRepository(CommentRepository):
    """SQLAlchemy-based implementation of CommentRepository.

    Comment is insert-only: save() raises CommentAlreadyExistsError
    if the entity already exists.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: CommentId) -> Comment | None:
        stmt = select(CommentTable).where(CommentTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: Comment) -> None:
        existing = await self._session.get(CommentTable, str(entity.id.value))
        if existing is not None:
            raise CommentAlreadyExistsError(
                f"Comment {entity.id.value} already exists."
            )
        comment_row = CommentTable(
            id=str(entity.id.value),
            record_id=str(entity.record_id.value),
            author_id=str(entity.author_id.value),
            body=entity.body.value,
            created_at=entity.created_at,
        )
        self._session.add(comment_row)
        await self._session.flush()

    @staticmethod
    def _to_entity(row: CommentTable) -> Comment:
        return Comment(
            id=CommentId.from_str(row.id),
            record_id=RecordId.from_str(row.record_id),
            author_id=UserId.from_str(row.author_id),
            body=CommentBody(row.body),
            created_at=row.created_at,
        )
