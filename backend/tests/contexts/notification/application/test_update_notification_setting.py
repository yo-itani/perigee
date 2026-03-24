"""Tests for UpdateNotificationSettingUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.notification.application.update_notification_setting import (
    UpdateNotificationSettingInput,
    UpdateNotificationSettingOutput,
    UpdateNotificationSettingUseCase,
)
from contexts.notification.domain.events import NotificationSettingUpdated
from contexts.notification.domain.exceptions import (
    InvalidReminderMinutesError,
    UnauthorizedOperationError,
)
from contexts.notification.domain.notification_setting import NotificationSetting
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.conftest import (
    FakeUnitOfWork,
    InMemoryNotificationSettingRepository,
    SpyEventDispatcher,
)


def _build_use_case(
    *,
    repo: InMemoryNotificationSettingRepository | None = None,
    uow: FakeUnitOfWork | None = None,
    event_dispatcher: SpyEventDispatcher | None = None,
) -> tuple[
    UpdateNotificationSettingUseCase,
    InMemoryNotificationSettingRepository,
    FakeUnitOfWork,
    SpyEventDispatcher,
]:
    r = repo or InMemoryNotificationSettingRepository()
    u = uow or FakeUnitOfWork()
    ed = event_dispatcher or SpyEventDispatcher()
    uc = UpdateNotificationSettingUseCase(
        notification_setting_repository=r,
        unit_of_work=u,
        event_dispatcher=ed,
    )
    return uc, r, u, ed


class TestUpdateNotificationSetting:
    """Tests for successful update."""

    async def test_creates_setting_on_first_update(self) -> None:
        user_id = UserId.generate()
        uc, repo, _uow, _ed = _build_use_case()

        output = await uc.execute(
            UpdateNotificationSettingInput(
                user_id=user_id,
                actor_id=user_id,
                reminder_minutes_before=60,
                is_enabled=False,
            )
        )

        assert isinstance(output, UpdateNotificationSettingOutput)
        assert output.user_id == user_id
        assert output.reminder_minutes_before == 60
        assert output.is_enabled is False

        saved = await repo.get_by_user_id(user_id)
        assert saved is not None
        assert saved.reminder_minutes_before == 60
        assert saved.is_enabled is False

    async def test_updates_existing_setting(self) -> None:
        user_id = UserId.generate()
        existing = NotificationSetting.create(
            user_id=user_id,
            reminder_minutes_before=30,
            is_enabled=True,
            now=datetime(2026, 3, 24, 10, 0),
        )
        uc, repo, _uow, _ed = _build_use_case()
        await repo.save(existing)

        output = await uc.execute(
            UpdateNotificationSettingInput(
                user_id=user_id,
                actor_id=user_id,
                reminder_minutes_before=120,
                is_enabled=False,
            )
        )

        assert output.reminder_minutes_before == 120
        assert output.is_enabled is False

    async def test_commits_transaction(self) -> None:
        user_id = UserId.generate()
        uc, _repo, uow, _ed = _build_use_case()

        await uc.execute(
            UpdateNotificationSettingInput(
                user_id=user_id,
                actor_id=user_id,
                reminder_minutes_before=15,
                is_enabled=True,
            )
        )

        assert uow.committed is True

    async def test_dispatches_event(self) -> None:
        user_id = UserId.generate()
        uc, _repo, _uow, ed = _build_use_case()

        await uc.execute(
            UpdateNotificationSettingInput(
                user_id=user_id,
                actor_id=user_id,
                reminder_minutes_before=45,
                is_enabled=True,
            )
        )

        updated_events = [
            e for e in ed.dispatched_events if isinstance(e, NotificationSettingUpdated)
        ]
        assert len(updated_events) == 1
        assert updated_events[0].user_id == user_id
        assert updated_events[0].reminder_minutes_before == 45
        assert updated_events[0].is_enabled is True

    async def test_dispatches_event_on_existing_update(self) -> None:
        user_id = UserId.generate()
        existing = NotificationSetting.create(
            user_id=user_id,
            reminder_minutes_before=30,
            is_enabled=True,
            now=datetime(2026, 3, 24, 10, 0),
        )
        uc, repo, _uow, ed = _build_use_case()
        await repo.save(existing)

        await uc.execute(
            UpdateNotificationSettingInput(
                user_id=user_id,
                actor_id=user_id,
                reminder_minutes_before=90,
                is_enabled=False,
            )
        )

        updated_events = [
            e for e in ed.dispatched_events if isinstance(e, NotificationSettingUpdated)
        ]
        assert len(updated_events) == 1
        assert updated_events[0].reminder_minutes_before == 90
        assert updated_events[0].is_enabled is False


class TestUpdateNotificationSettingErrors:
    """Tests for error conditions."""

    async def test_raises_when_actor_is_different_user(self) -> None:
        user_id = UserId.generate()
        other_id = UserId.generate()
        uc, _repo, _uow, _ed = _build_use_case()

        with pytest.raises(
            UnauthorizedOperationError, match="another user's notification setting"
        ):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=other_id,
                    reminder_minutes_before=30,
                    is_enabled=True,
                )
            )

    async def test_raises_when_reminder_below_minimum(self) -> None:
        user_id = UserId.generate()
        uc, _repo, _uow, _ed = _build_use_case()

        with pytest.raises(InvalidReminderMinutesError):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=user_id,
                    reminder_minutes_before=4,
                    is_enabled=True,
                )
            )

    async def test_raises_when_reminder_above_maximum(self) -> None:
        user_id = UserId.generate()
        uc, _repo, _uow, _ed = _build_use_case()

        with pytest.raises(InvalidReminderMinutesError):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=user_id,
                    reminder_minutes_before=1441,
                    is_enabled=True,
                )
            )

    async def test_does_not_commit_on_authorization_error(self) -> None:
        user_id = UserId.generate()
        other_id = UserId.generate()
        uc, _repo, uow, _ed = _build_use_case()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=other_id,
                    reminder_minutes_before=30,
                    is_enabled=True,
                )
            )

        assert uow.committed is False

    async def test_does_not_dispatch_events_on_error(self) -> None:
        user_id = UserId.generate()
        other_id = UserId.generate()
        uc, _repo, _uow, ed = _build_use_case()

        with pytest.raises(UnauthorizedOperationError):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=other_id,
                    reminder_minutes_before=30,
                    is_enabled=True,
                )
            )

        assert ed.dispatched_events == []

    async def test_does_not_save_on_validation_error(self) -> None:
        """When validation fails, nothing should be persisted."""
        user_id = UserId.generate()
        uc, repo, _uow, _ed = _build_use_case()

        with pytest.raises(InvalidReminderMinutesError):
            await uc.execute(
                UpdateNotificationSettingInput(
                    user_id=user_id,
                    actor_id=user_id,
                    reminder_minutes_before=0,
                    is_enabled=True,
                )
            )

        assert await repo.get_by_user_id(user_id) is None
