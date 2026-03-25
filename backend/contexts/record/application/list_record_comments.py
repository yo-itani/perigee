"""Use case: List comments for a published Record (read-only).

Only users who can see the record (organizer, counterpart, viewers) can
list its comments. Comments on draft records are not accessible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contexts.record.domain.comment_repository import CommentRepository
from contexts.record.domain.exceptions import (
    RecordNotPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import CommentId, RecordId, RecordStatus
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class CommentDTO:
    """Single comment item in the output."""

    comment_id: CommentId
    author_id: UserId
    body: str
    created_at: datetime


@dataclass(frozen=True)
class ListRecordCommentsInput:
    """Input DTO for ListRecordCommentsUseCase."""

    record_id: RecordId
    actor_id: UserId


@dataclass(frozen=True)
class ListRecordCommentsOutput:
    """Output DTO for ListRecordCommentsUseCase."""

    comments: list[CommentDTO]


class ListRecordCommentsUseCase:
    """List all comments for a published record.

    Authorization:
    - Record must be published.
    - Actor must be visible to the record (organizer, counterpart, or viewer).

    This is a read-only query; no UoW or EventDispatcher needed.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        comment_repository: CommentRepository,
    ) -> None:
        self._record_repository = record_repository
        self._comment_repository = comment_repository

    async def execute(
        self, input_dto: ListRecordCommentsInput
    ) -> ListRecordCommentsOutput:
        record = await self._record_repository.get_by_id(input_dto.record_id)
        if record is None:
            raise RecordNotFoundError(input_dto.record_id)

        if record.status != RecordStatus.PUBLISHED:
            raise RecordNotPublishedError(
                "Comments are only available for published records."
            )

        if not record.is_visible_to(input_dto.actor_id):
            raise UnauthorizedOperationError(
                "You do not have permission to view comments on this record."
            )

        comments = await self._comment_repository.list_by_record_id(input_dto.record_id)

        return ListRecordCommentsOutput(
            comments=[
                CommentDTO(
                    comment_id=c.id,
                    author_id=c.author_id,
                    body=c.body.value,
                    created_at=c.created_at,
                )
                for c in comments
            ]
        )
