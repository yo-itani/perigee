"""Tests for MarkNotificationAsReadUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.notification.application.mark_notification_as_read import (
    MarkNotificationAsReadInput,
    MarkNotificationAsReadUseCase,
    NotificationNotFoundError,
)
from contexts.notification.domain.exceptions import (
    NotificationAlreadyReadError,
    UnauthorizedOperationError,
)
from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_record import NotificationRecord
from contexts.notification.domain.value_objects import (
    NotificationRecordId,
    NotificationType,
)
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.conftest import (
    FakeUnitOfWork,
    InMemoryNotificationRecordRepository,
)


def _make_record(
    *,
    recipient_id: UserId | None = None,
    now: datetime | None = None,
) -> NotificationRecord:
    return NotificationRecord.create(
        recipient_id=recipient_id or UserId.generate(),
        message=NotificationMessage(
            notification_type=NotificationType.SCHEDULE_CREATED,
            title="Test",
            body="Test body",
        ),
        now=now or datetime(2026, 3, 26, 10, 0),
    )


def _build_use_case() -> tuple[
    MarkNotificationAsReadUseCase,
    InMemoryNotificationRecordRepository,
    FakeUnitOfWork,
]:
    repo = InMemoryNotificationRecordRepository()
    uow = FakeUnitOfWork()
    uc = MarkNotificationAsReadUseCase(
        notification_record_repository=repo,
        unit_of_work=uow,
    )
    return uc, repo, uow


class TestMarkNotificationAsRead:
    """Tests for successful mark-as-read."""

    async def test_marks_notification_as_read(self) -> None:
        uc, repo, uow = _build_use_case()
        user_id = UserId.generate()
        record = _make_record(recipient_id=user_id)
        await repo.save(record)

        await uc.execute(
            MarkNotificationAsReadInput(
                notification_id=record.id,
                actor_id=user_id,
            )
        )

        saved = await repo.get_by_id(record.id)
        assert saved is not None
        assert saved.is_read is True
        assert saved.read_at is not None

    async def test_commits_transaction(self) -> None:
        uc, repo, uow = _build_use_case()
        user_id = UserId.generate()
        record = _make_record(recipient_id=user_id)
        await repo.save(record)

        await uc.execute(
            MarkNotificationAsReadInput(
                notification_id=record.id,
                actor_id=user_id,
            )
        )

        assert uow.committed is True


class TestMarkNotificationAsReadErrors:
    """Tests for error conditions."""

    async def test_raises_when_notification_not_found(self) -> None:
        uc, _repo, _uow = _build_use_case()

        with pytest.raises(NotificationNotFoundError, match="not found"):
            await uc.execute(
                MarkNotificationAsReadInput(
                    notification_id=NotificationRecordId.generate(),
                    actor_id=UserId.generate(),
                )
            )

    async def test_raises_when_actor_is_not_recipient(self) -> None:
        uc, repo, _uow = _build_use_case()
        owner = UserId.generate()
        other = UserId.generate()
        record = _make_record(recipient_id=owner)
        await repo.save(record)

        with pytest.raises(
            UnauthorizedOperationError,
            match="another user's notification",
        ):
            await uc.execute(
                MarkNotificationAsReadInput(
                    notification_id=record.id,
                    actor_id=other,
                )
            )

    async def test_raises_when_already_read(self) -> None:
        uc, repo, _uow = _build_use_case()
        user_id = UserId.generate()
        record = _make_record(recipient_id=user_id)
        record.mark_as_read(now=datetime(2026, 3, 26, 11, 0))
        await repo.save(record)

        with pytest.raises(
            NotificationAlreadyReadError, match="already marked as read"
        ):
            await uc.execute(
                MarkNotificationAsReadInput(
                    notification_id=record.id,
                    actor_id=user_id,
                )
            )
