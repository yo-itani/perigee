"""Tests for GetNotificationSettingUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from contexts.notification.application.get_notification_setting import (
    GetNotificationSettingInput,
    GetNotificationSettingOutput,
    GetNotificationSettingUseCase,
)
from contexts.notification.domain.exceptions import UnauthorizedOperationError
from contexts.notification.domain.notification_setting import NotificationSetting
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.conftest import (
    InMemoryNotificationSettingRepository,
)


def _build_use_case(
    *,
    repo: InMemoryNotificationSettingRepository | None = None,
) -> tuple[GetNotificationSettingUseCase, InMemoryNotificationSettingRepository]:
    r = repo or InMemoryNotificationSettingRepository()
    uc = GetNotificationSettingUseCase(notification_setting_repository=r)
    return uc, r


class TestGetNotificationSetting:
    """Tests for successful retrieval."""

    async def test_returns_persisted_setting(self) -> None:
        user_id = UserId.generate()
        setting = NotificationSetting.create(
            user_id=user_id,
            reminder_minutes_before=60,
            is_enabled=False,
            now=datetime(2026, 3, 24, 10, 0),
        )
        uc, repo = _build_use_case()
        await repo.save(setting)

        output = await uc.execute(
            GetNotificationSettingInput(user_id=user_id, actor_id=user_id)
        )

        assert isinstance(output, GetNotificationSettingOutput)
        assert output.user_id == user_id
        assert output.reminder_minutes_before == 60
        assert output.is_enabled is False

    async def test_returns_default_when_no_persisted_setting(self) -> None:
        user_id = UserId.generate()
        uc, _repo = _build_use_case()

        output = await uc.execute(
            GetNotificationSettingInput(user_id=user_id, actor_id=user_id)
        )

        assert output.user_id == user_id
        assert output.reminder_minutes_before == 30
        assert output.is_enabled is True

    async def test_default_not_saved_to_repository(self) -> None:
        """When returning defaults, the setting should NOT be persisted."""
        user_id = UserId.generate()
        uc, repo = _build_use_case()

        await uc.execute(GetNotificationSettingInput(user_id=user_id, actor_id=user_id))

        assert await repo.get_by_user_id(user_id) is None


class TestGetNotificationSettingErrors:
    """Tests for error conditions."""

    async def test_raises_when_actor_is_different_user(self) -> None:
        user_id = UserId.generate()
        other_id = UserId.generate()
        uc, _repo = _build_use_case()

        with pytest.raises(
            UnauthorizedOperationError, match="another user's notification setting"
        ):
            await uc.execute(
                GetNotificationSettingInput(user_id=user_id, actor_id=other_id)
            )
