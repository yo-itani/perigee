"""Use case: Add a Comment to a published Record.

Any user who can see the record (organizer, counterpart, viewer) can
add a comment. Comments are insert-only. After a successful commit
the RecordCommentAdded domain event is dispatched (triggers Slack
notification).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.record.domain.comment import Comment
from contexts.record.domain.comment_body import CommentBody
from contexts.record.domain.comment_repository import CommentRepository
from contexts.record.domain.exceptions import (
    RecordNotPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.read_status_repository import ReadStatusRepository
from contexts.record.domain.record_repository import RecordRepository
from contexts.record.domain.value_objects import CommentId, RecordId, RecordStatus
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class RecordNotFoundError(Exception):
    """Raised when the specified record does not exist."""

    def __init__(self, record_id: RecordId) -> None:
        self.record_id = record_id
        super().__init__(f"Record not found: {record_id.value}")


@dataclass(frozen=True)
class AddCommentInput:
    """Input DTO for AddCommentUseCase."""

    record_id: RecordId
    actor_id: UserId
    body: CommentBody


@dataclass(frozen=True)
class AddCommentOutput:
    """Output DTO for AddCommentUseCase."""

    comment_id: CommentId


class AddCommentUseCase:
    """Add a comment to a published record.

    Workflow:
    1. Load the record and verify it exists.
    2. Verify the record is published.
    3. Verify the actor is visible to the record (organizer, counterpart, or viewer).
    4. Create the comment (insert-only).
    5. Save within a transaction.
    6. Dispatch domain events after commit.
    """

    def __init__(
        self,
        *,
        record_repository: RecordRepository,
        comment_repository: CommentRepository,
        read_status_repository: ReadStatusRepository,
        unit_of_work: UnitOfWork,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._record_repository = record_repository
        self._comment_repository = comment_repository
        self._read_status_repository = read_status_repository
        self._unit_of_work = unit_of_work
        self._event_dispatcher = event_dispatcher

    async def execute(self, input_dto: AddCommentInput) -> AddCommentOutput:
        now = datetime.now(UTC)

        async with self._unit_of_work:
            record = await self._record_repository.get_by_id(input_dto.record_id)
            if record is None:
                raise RecordNotFoundError(input_dto.record_id)

            if record.status != RecordStatus.PUBLISHED:
                raise RecordNotPublishedError(
                    "Comments can only be added to published records."
                )

            if not record.is_visible_to(input_dto.actor_id):
                raise UnauthorizedOperationError(
                    "Only users who can view the record may add comments."
                )

            comment = Comment.create(
                record_id=record.id,
                author_id=input_dto.actor_id,
                body=input_dto.body,
                now=now,
            )

            # Update latest_activity_at on the record
            record.notify_comment_added(now)

            # Auto-mark commenter as read (upsert for concurrency safety)
            read_status = ReadStatus.create(
                record_id=record.id,
                user_id=input_dto.actor_id,
                now=now,
            )
            await self._read_status_repository.upsert(read_status)

            await self._comment_repository.save(comment)
            await self._record_repository.save(record)
            await self._unit_of_work.commit()

        # Dispatch events after successful commit
        events: list[DomainEvent] = list(comment.collect_events())
        await self._event_dispatcher.dispatch(events)

        return AddCommentOutput(comment_id=comment.id)
